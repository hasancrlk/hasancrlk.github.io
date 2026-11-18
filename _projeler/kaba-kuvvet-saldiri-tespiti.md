---
title: "Bir giriş logundan kaba kuvvet saldırısını ayıklamak"
kisa: SSH ve web giriş loglarından şifre deneme saldırılarını bulan, her alarmı gerekçesiyle veren analiz servisi.
ozet: "Her başarısız girişe alarm veren bir sistem bir hafta sonra kimsenin bakmadığı bir sisteme dönüşür. Ben de şunu sordum: şifresini unutan çalışanı, kapıyı yoklayan bottan nasıl ayırırım?"
date: 2026-09-18
teknolojiler: [Python, FastAPI, SQLAlchemy, PostgreSQL, pytest, Docker]
repo: https://github.com/hasancrlk/kaba-kuvvet-saldiri-tespiti
kategori: guvenlik
sira: 1
ref: authwatch
---

Bu proje EMT Cyber stajında verilen ödevlerden biriydi: SSH ve web
sunucularının giriş loglarını okuyup kaba kuvvet (brute-force) saldırılarını
tespit etmek. İşin kolay kısmı saldırıyı bulmak. Zor kısmı, bulduğunuz şeyin
gerçekten saldırı olup olmadığına karar vermek.

İki örneğe bakalım. Bunlar depodaki örnek log dosyasından; IP adresleri
belgelendirme için ayrılmış aralıklardan:

```
Sep 17 03:12:01 srv01 sshd[4101]: Failed password for invalid user admin from 203.0.113.5
Sep 17 03:12:04 srv01 sshd[4102]: Failed password for invalid user oracle from 203.0.113.5
Sep 17 03:12:07 srv01 sshd[4103]: Failed password for root from 203.0.113.5
Sep 17 03:12:10 srv01 sshd[4104]: Failed password for invalid user postgres from 203.0.113.5
```

Aynı IP, üç saniye arayla, her seferinde başka bir kullanıcı adı. Bu bir bot.
Şimdi de şuna bakın:

```
Sep 17 09:42:10 srv01 sshd[5210]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:16 srv01 sshd[5211]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:41 srv01 sshd[5212]: Failed password for deniz from 198.51.100.7
```

Bu büyük ihtimalle şifresini hatırlamaya çalışan biri. İkisini ayırmak
sektörde iyi bilinen bir sorun ve projeyi bu sorunun etrafında kurdum.

## Önce saymayı doğru yapmak

Temel kural şu: aynı IP'den 60 saniyede 5 başarısız deneme varsa alarm ver.
Ama sayacı her dakika sıfırlarsanız saldırgan bir dakikanın sonunda 4,
sonrakinin başında 4 deneme yapıp eşiğin altında kalır. Bu yüzden **kayan
pencere** kullandım. Her IP için bir `deque` tutuyorum ve yeni bir deneme
geldiğinde pencereden düşen eski kayıtları atıyorum:

```python
bucket.append(event)
while bucket and event.timestamp - bucket[0].timestamp > window:
    bucket.popleft()
if len(bucket) >= threshold:
    alarm_uret()
```

Her kayıt kuyruğa bir kez girip bir kez çıktığı için büyük bir log tek
geçişte işleniyor. Sabit pencerenin kaçırdığı o 4+4'lük dizi depoda ayrı bir
test olarak duruyor.

Bir de soğuma süresi ekledim. Eşik aşıldıktan sonra her yeni denemeye ayrı
alarm üretseydim 500 denemelik bir saldırı 496 alarm demekti. Aynı IP için 5
dakika boyunca yeni alarm yazılmıyor.

## Kullanıcıyı bottan ayırmak

Eşiği geçen her yığını saldırı saymak yerine her alarma bir güven puanı
veriyorum. Puan denemelerin biçimine bakıyor:

- Üç ve daha fazla farklı kullanıcı adı denenmişse puan artıyor, tek bir
  kullanıcı adıysa düşüyor.
- `invalid user` satırları, yani var olmayan hesaplara yapılan denemeler,
  kullanıcı taramasının işareti.
- Denemeler arasındaki sürelerin ne kadar düzenli olduğuna bakıyorum. İnsan
  düzensiz aralıklarla dener, otomasyon saat gibi.
- Aynı IP'den daha önce başarılı giriş yapılmışsa puan düşüyor.

Sonuç `high`, `medium` ya da `low` olarak etiketleniyor ve her alarm bu
kararın gerekçesini yazıyor. Yukarıdaki iki örnek için çıktı şöyle:

```
203.0.113.5   güven: high (0.95)
  - 5 farkli kullanici adi denendi (kullanici tarama).
  - 4 deneme var olmayan kullanici adina yapildi.
  - Denemeler neredeyse sabit araliklarla geldi (otomasyon izi).

198.51.100.7  güven: low (0.0)
  - Tek kullanici adi - parolasini unutmus bir kullanici olabilir.
  - Bu IP daha once basariyla giris yapmis (bilinen kaynak).
```

Düşük güvenli alarmları silmiyorum, yalnızca etiketliyorum. Neyin önemsiz
olduğuna analist karar vermeli; araç sadece sıralamayı kolaylaştırıyor.

Bir ayrıntı daha: web loglarında kullanıcı adı çoğu zaman `-` olarak geliyor.
Bunu "tek kullanıcı" sayıp puanı düşürseydim gerçek bir bot yığınını haksız
yere masum gösterirdim. Bilgi yoksa indirim de yok.

## Başarısızlıkların ardından gelen başarı

Bir IP aynı hesaba art arda başarısız denemeler yapıp sonra o hesapla
başarıyla girerse bu ayrı bir alarm: `possible_account_takeover`. Burada
kullanıcı adının eşleşmesini şart koştum. `admin` hesabına saldırıdan sonra
`deploy` ile yapılan sıradan bir giriş bu kapsama girmiyor.

## Neleri yapmıyor?

Tespit IP bazlı olduğu için her IP'den az sayıda deneme yapan bir botnet
eşiğe takılmıyor. Her yükleme ayrı işlendiği için iki dosyaya bölünmüş bir
saldırı da ikiye ayrılabiliyor. `X-Forwarded-For` başlığını okumuyorum ve
servisin kendisinde kimlik doğrulama yok; iç ağda ya da bir ters vekil
arkasında çalıştırılmalı.

Proje 48 testle geliyor. `docker compose up` ile PostgreSQL'li olarak
ayağa kalkıyor ve örnek log depoda olduğu için hemen deneyebilirsiniz.
