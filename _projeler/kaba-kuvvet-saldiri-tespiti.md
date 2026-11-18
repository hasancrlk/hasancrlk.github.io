---
title: "Bir giriş logundan kaba kuvvet saldırısını ayıklamak"
kisa: SSH ve web giriş loglarından şifre deneme saldırılarını bulan, her alarmı gerekçesiyle veren analiz servisi.
ozet: "SSH ve web sunucularının giriş loglarını okuyup kaba kuvvet (brute-force) saldırılarını tespit eden bir servis. Odak noktası, şifresini unutan bir kullanıcıyı saldırgan olarak işaretlememek."
date: 2026-09-18
teknolojiler: [Python, FastAPI, SQLAlchemy, PostgreSQL, pytest, Docker]
repo: https://github.com/hasancrlk/kaba-kuvvet-saldiri-tespiti
kategori: guvenlik
sira: 1
ref: authwatch
---

İnternete açık bir SSH sunucusunun `auth.log` dosyası aşağı yukarı şöyle
görünür:

```
Sep 17 03:12:01 srv01 sshd[4101]: Failed password for invalid user admin from 203.0.113.5
Sep 17 03:12:04 srv01 sshd[4102]: Failed password for invalid user oracle from 203.0.113.5
Sep 17 03:12:07 srv01 sshd[4103]: Failed password for root from 203.0.113.5
Sep 17 03:12:10 srv01 sshd[4104]: Failed password for invalid user postgres from 203.0.113.5
```

Aynı IP, üç saniye arayla, her seferinde farklı bir kullanıcı adı. Bu tablo bir
botun kapıyı yokladığını açıkça gösteriyor. Aynı dosyada şu satırlar da var:

```
Sep 17 09:42:10 srv01 sshd[5210]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:16 srv01 sshd[5211]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:41 srv01 sshd[5212]: Failed password for deniz from 198.51.100.7
```

Bu ise büyük ihtimalle şifresini hatırlamaya çalışan bir çalışan. İki durumu
birbirinden ayırmak sektörde iyi bilinen bir sorun: her başarısız girişe alarm
veren bir sistem kısa sürede gürültüye boğulur ve alarmlara bakılmaz olur. Bu
projeyi EMT Cyber stajı sırasında verilen ödevlerden biri olarak bu sorunun
etrafında kurdum.

Aşağıdaki satırlar depodaki örnek log dosyasından alınmıştır; IP adresleri
belgelendirme için ayrılmış aralıklardandır.

## Eşiği doğru saymak

Temel kural "aynı IP'den 60 saniyede 5 başarısız deneme varsa alarm" şeklinde.
Bu kuralın sayacı her dakika sıfırlanırsa saldırgan bir pencerenin sonunda 4,
yeni pencerenin başında 4 deneme yaparak eşiğin altında kalabilir. Bu nedenle
sayım **kayan pencere** ile yapılıyor: her IP için bir `deque` tutuluyor ve
yeni bir başarısız deneme geldiğinde pencerenin dışına düşen eski kayıtlar
atılıyor.

```python
bucket.append(event)
while bucket and event.timestamp - bucket[0].timestamp > window:
    bucket.popleft()
if len(bucket) >= threshold:
    alarm_uret()
```

Her kayıt kuyruğa bir kez girip bir kez çıktığı için maliyet doğrusaldır;
büyük bir log tek geçişte işlenir. Sabit pencerenin kaçırdığı 4+4 dizisi
depoda ayrı bir test olarak duruyor.

Eşik aşıldıktan sonra her yeni deneme için alarm üretilmemesi için bir soğuma
süresi de var. Varsayılan değer 300 saniye; bu süre boyunca aynı IP için yeni
alarm yazılmıyor.

## Kullanıcı ile botu ayırmak

Eşiği geçen her yığın saldırı değildir. Servis her alarm için bir güven puanı
hesaplıyor ve bu puanı denemelerin biçimine bakarak oluşturuyor:

- **Kullanıcı adı çeşitliliği.** Üç ve daha fazla farklı kullanıcı adı
  denenmişse puan artar; tek bir kullanıcı adıysa azalır.
- **Var olmayan kullanıcılar.** `invalid user` satırları kullanıcı taramasının
  işaretidir ve puanı yükseltir.
- **Aralıkların düzenliliği.** Denemeler arasındaki sürelerin varyasyon
  katsayısı hesaplanır. İnsan düzensiz aralıklarla dener, otomasyon sabit
  aralıklarla.
- **Deneme yoğunluğu.** Eşiğin üç katı ve üzerindeki deneme sayısı puanı
  artırır.
- **Geçmiş.** Aynı IP'den daha önce başarılı giriş yapılmışsa puan düşer.

Sonuç `high`, `medium` ya da `low` olarak etiketlenir ve her alarm bu kararın
gerekçesini cümle olarak taşır. Yukarıdaki iki örnek için çıktı şöyle:

```
203.0.113.5   güven: high (0.95)
  - 5 farkli kullanici adi denendi (kullanici tarama).
  - 4 deneme var olmayan kullanici adina yapildi.
  - Denemeler neredeyse sabit araliklarla geldi (otomasyon izi).

198.51.100.7  güven: low (0.0)
  - Tek kullanici adi - parolasini unutmus bir kullanici olabilir.
  - Bu IP daha once basariyla giris yapmis (bilinen kaynak).
```

Düşük güvenli alarmlar silinmiyor, yalnızca etiketleniyor. Hangisinin
önemsiz olduğuna analist karar verir; servis yalnızca sıralamayı kolaylaştırır.

Web erişim loglarında kullanıcı adı çoğunlukla `-` olarak gelir. Bu durumda
"tek kullanıcı adı" indirimi uygulanmıyor; aksi hâlde gerçek bir bot
yığınının puanı haksız yere düşerdi.

## Başarısızlıkların ardından gelen başarı

Aynı IP'den aynı kullanıcı adına art arda başarısız denemeler yapılıp ardından
o hesapla başarılı giriş gerçekleşirse servis ayrı bir alarm üretiyor:
`possible_account_takeover`. Burada kullanıcı adının eşleşmesi şart.
`admin` hesabına yapılan saldırıdan sonra `deploy` hesabıyla yapılan olağan
bir giriş bu kapsama girmiyor.

## Desteklenen loglar

SSH `auth.log`, nginx/apache combined log ve JSON satırları okunabiliyor.
Biçime uymayan satırlar sayılıyor ve örnekleri saklanıyor; böylece "dosyanın
ne kadarı okunamadı" sorusunun cevabı her yüklemede görünüyor. `auth.log`
tarihte yıl bilgisi taşımadığı için yıl yükleme sırasında parametre olarak
veriliyor.

## Kapsam dışında kalanlar

- **Dağıtık saldırılar.** Tespit IP bazlı çalışıyor. Her IP'den az sayıda
  deneme yapan bir botnet eşiğe ulaşmaz; bunun için kullanıcı ya da ağ (ASN)
  bazlı bir boyut eklemek gerekir.
- **Yüklemeler arası durum.** Her yükleme ayrı işleniyor. İki dosyaya bölünmüş
  bir saldırı ikiye ayrılabilir.
- **Vekil sunucu arkası.** `X-Forwarded-For` okunmuyor.
- **Kimlik doğrulama.** Servisin kendisi açık; iç ağda ya da bir ters vekil
  arkasında çalıştırılmalı.

Proje 48 test ile birlikte geliyor ve `docker compose up` ile PostgreSQL'li
olarak ayağa kalkıyor. Örnek log dosyası depoda bulunduğu için kurulumdan
hemen sonra denenebilir.
