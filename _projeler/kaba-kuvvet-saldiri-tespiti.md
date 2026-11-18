---
title: "Şifresini unutan kullanıcı mı, bot mu? Loglardan kaba kuvvet saldırısı tespiti"
kisa: SSH ve web giriş loglarından şifre deneme saldırılarını bulan, her alarmı gerekçesiyle veren analiz servisi.
ozet: "Sunucu loglarını okuyup kaba kuvvet (brute-force) saldırılarını bulan bir servis yazdım. Asıl iş saldırıyı bulmak değil, şifresini unutan çalışanı saldırgan sanmamaktı."
date: 2026-09-18
teknolojiler: [Python, FastAPI, SQLAlchemy, PostgreSQL, pytest, Docker]
repo: https://github.com/hasancrlk/kaba-kuvvet-saldiri-tespiti
kategori: guvenlik
sira: 1
ref: authwatch
---

## Problem

Bir sunucuya yapılan her giriş denemesi log dosyasına bir satır olarak düşer.
İnternete açık herhangi bir SSH sunucusunun `auth.log` dosyasına bakarsanız
dakikada birkaç kez `Failed password for invalid user admin` gibi satırlar
görürsünüz. Botlar sürekli kapı yokluyor.

Kural basit görünür: "aynı IP'den 60 saniyede 5 başarısız deneme varsa alarm
ver." Bu kuralı yazmak beş dakika sürer. Ama iki yerde çuvallar:

1. Saldırgan kuralı kolayca atlatır.
2. Şifresini unutup üç dört kez yanlış yazan çalışan da alarm üretir. Bir
   süre sonra kimse alarmlara bakmaz.

Bu projede ikisini de çözmeye çalıştım.

## Zor kısım 1: Sabit pencere atlatılır

"Her 60 saniyede sayacı sıfırla" yaklaşımında eşik 5 ise saldırgan şunu yapar:
bir pencerenin sonunda 4 deneme, sıfırlamadan hemen sonra 4 deneme daha.

```
pencere 1                          pencere 2
├───────────────────────────┤      ├──────────────────────
     ✗  ✗  ✗  ✗  (4 deneme)         ✗  ✗  ✗  ✗  (4 deneme)
                         ↑ 55. sn   ↑ 62. sn

sabit pencere : iki ayrı pencerede 4'er deneme → ALARM YOK
kayan pencere : 62. sn'de son 60 sn'ye bak → 8 deneme → ALARM
```

Çözüm **kayan pencere**. Her IP için bir `deque` tutuyorum. Yeni bir başarısız
deneme gelince pencereden çıkanları baştan atıyorum:

```python
bucket.append(event)
while bucket and event.timestamp - bucket[0].timestamp > window:
    bucket.popleft()          # pencereden çıkanları at
if len(bucket) >= threshold:
    alarm_uret()
```

Her olay kuyruğa bir kez girip bir kez çıktığı için maliyet doğrusal. Bir
milyon satırlık log tek geçişte işleniyor. Yukarıdaki saldırı dizisi depoda
birebir test olarak duruyor.

Bir de **soğuma süresi** ekledim. Eşik aşıldıktan sonra her yeni deneme alarm
üretseydi 500 denemelik bir saldırı 496 alarm demekti. Aynı IP için 5 dakika
boyunca tekrar alarm üretilmiyor.

## Zor kısım 2: İnsanı bottan ayırmak

Eşiği geçen her yığın saldırı değil. Fark denemelerin **şeklinde**:

| Sinyal | İnsan | Bot | Puan etkisi |
|---|---|---|---:|
| Denenen kullanıcı adı sayısı | 1 | çok | 3+ ise +0.25, tekse −0.15 |
| Var olmayan kullanıcı (`invalid user`) | yok | sık | +0.20 |
| Denemeler arası düzenlilik | düzensiz | saat gibi | düzenliyse +0.15 |
| Eşiğin kaç katı deneme | az | çok | 3 katıysa +0.25 |
| Bu IP'den daha önce başarılı giriş | genelde var | genelde yok | −0.20 |

Düzenliliği denemeler arası boşlukların **varyasyon katsayısından**
hesaplıyorum. İnsan 3 saniye, sonra 12, sonra 40 saniye bekler. Bot saat gibi
gelir. Toplam puan `yüksek / orta / düşük` diye etiketleniyor ve her alarm
gerekçesini düz cümleyle yazıyor. Depodaki örnek logdan iki gerçek çıktı:

```
203.0.113.5  →  5 farklı kullanıcı, 4'ü yok, tam 3 sn aralıklarla
                güven: yüksek (0.95)
                "5 farkli kullanici adi denendi (kullanici tarama)."
                "Denemeler neredeyse sabit araliklarla geldi (otomasyon izi)."

198.51.100.7 →  tek hesap, düzensiz aralık, sabah aynı IP'den başarılı giriş
                güven: düşük (0.0)
                "Tek kullanici adi - parolasini unutmus bir kullanici olabilir."
```

İki tasarım kararı var. Birincisi: **düşük güvenli alarm silinmiyor**, yalnızca
etiketleniyor. Kendi kendini süzen bir sistem gerçek bir saldırıyı da sessizce
yutabilir. Kararı analist verir. İkincisi: web loglarında kullanıcı adı
çoğunlukla `-` gelir. Bunu "tek kullanıcı" sayıp puan indirimi yapsaydım
gerçek bir bot yığınının puanını haksız yere düşürürdüm. Sinyal yoksa indirim
de yok.

## Hesap ele geçirme

Aynı IP'den **aynı kullanıcı adına** art arda başarısız denemeler gelip
ardından o hesapla başarılı giriş yapılırsa bu ayrı bir alarm türü:

```
22:05:00  ✗ hasan    ┐
  ...                ├─ 6 başarısız deneme
22:05:45  ✗ hasan    ┘
22:05:54  ✓ hasan    ← olası hesap ele geçirme (güven: yüksek)
```

Kullanıcı adı eşleşmesini zorunlu tuttum. `admin` hesabına 6 kez saldırılıp
sonra `deploy` hesabıyla normal giriş yapılması ele geçirme değil. Bunu
eşleştirseydim her sabah işe gelen geliştirici alarm konusu olurdu.

## Log ayrıştırma

Üç biçim destekleniyor: SSH `auth.log`, nginx/apache combined log ve JSON
satırları. Okunamayan satırlar atılmıyor, sayılıyor ve örnekleri saklanıyor.
"30 satırın 1'i okunamadı, işte o satır" diyebilmek, sessizce atmaktan iyi.
Küçük bir tuzak: `auth.log` tarihte yıl yazmaz (`Sep 17 03:12:01`). Yıl
yüklemede parametre olarak veriliyor.

## Bilerek yapmadıklarım

- **Dağıtık saldırı görülmez.** Tespit IP bazlı. Her IP'den 2 deneme yapan
  bir botnet eşiği hiç geçmez. Bunun için kullanıcı ya da ağ (ASN) bazlı bir
  boyut gerekir.
- **Yüklemeler arası durum taşınmıyor.** İki ayrı dosyaya bölünmüş bir saldırı
  ikiye ayrılabilir. Gerçek zamanlı akış için durumun kalıcı tutulması lazım.
- **Proxy arkası IP okunmuyor.** `X-Forwarded-For` başlığına bakılmıyor.

## Öğrendiklerim

En çok şunu öğrendim: bir tespit sisteminin değeri yakaladığı saldırı
sayısında değil, **güvenilen alarm** sayısında. Gerekçesiz bir "ALARM"
satırına bir süre sonra kimse bakmıyor. "Neden" sorusunu cevaplayan alarma
bakılıyor. Proje 48 testle geliyor. En sevdiğim test, sabit pencerenin
kaçırdığı diziyi kayan pencerenin yakaladığını gösteren test.
