---
title: "nmap kullanıyordum, sonra kendi port tarayıcımı yazdım"
kisa: Açık TCP portlarını eşzamanlı tarayıp arkadaki servisi banner'dan tahmin eden, izinsiz hedefi reddeden tarayıcı.
ozet: "Daha önce nmap ile çalışmıştım. Bu projede onun en çok kullanılan kısmını, TCP connect taramasını ve banner okumayı, asyncio ile sıfırdan yazdım ve araca kötüye kullanıma karşı bir kapsam kapısı ekledim."
date: 2026-09-18
teknolojiler: [Python, asyncio, FastAPI, SQLAlchemy, argparse, Docker]
repo: https://github.com/hasancrlk/port-tarayici
kategori: guvenlik
sira: 4
ref: portscout
---

Bu projeden önce port taramasını nmap üzerinden kullanıcı olarak
biliyordum. Komutu yazar, çıktıyı okurdum. Aynı işi kendi kodumla yapmak, nmap
çıktısındaki her kelimenin arkasında hangi ağ davranışı olduğunu görmemi
sağladı.

PortScout nmap'in yerini almak için değil, onun en sık kullanılan bölümünü
anlamak için yazıldı: TCP connect taraması ve servislerin kendilerini
tanıttığı ilk satırın (banner) okunması.

```
$ python -m cli scan 127.0.0.1 -p top100
PORT    DURUM     SERVIS     URUN / BANNER
22      open      ssh        OpenSSH/SSH: OpenSSH_9.6
```

## Eşzamanlılık modeli

Port taraması büyük ölçüde beklemekten ibarettir. Her bağlantı ya el
sıkışmayı tamamlar ya da zaman aşımı dolana kadar cevap bekler; işlemci bu
sürede neredeyse hiç çalışmaz. Bu iş yükü için `asyncio` seçildi.

Belirleyici olan, zaman aşımının nasıl ele alındığı. Bir thread havuzunda
`future.result(timeout=...)` beklemeyi bırakır ama iş parçacığını serbest
bırakmaz; bağlantı işletim sistemi tarafından kapatılana kadar havuzda yer
tutmaya devam eder. Cevap vermeyen bir hostta bu durum havuzu hızla doldurur.
`asyncio.wait_for` ise coroutine'i iptal eder ve yer hemen boşalır.

Eşzamanlılık sınırsız bırakılmadı. `asyncio.Semaphore` olmadan binlerce
bağlantı aynı anda açılmaya çalışır: yerel tarafta dosya tanıtıcısı sınırına
takılır, karşı tarafta ise bir SYN selini andırır. Varsayılan değer 200
eşzamanlı bağlantı ve `--concurrency` ile değiştirilebiliyor.

Yaklaşık bir ölçüm vermek gerekirse: cevap vermeyen bir hostta 1.000 port,
1 saniye zaman aşımı ve 200 eşzamanlı bağlantıyla tarama 5 saniye civarında
tamamlanıyor.

## Üç port durumu

Tarayıcı her port için üç durumdan birini raporluyor:

- **open:** TCP el sıkışması tamamlandı, port dinleniyor.
- **closed:** Karşı taraf `RST` gönderdi. Host ayakta ama bu portta servis yok.
- **filtered:** Hiç cevap gelmedi. Arada bir güvenlik duvarı olabilir ya da
  host kapalı olabilir.

`closed` ile `filtered` arasındaki fark keşif açısından anlamlıdır. Bütün
portlar `filtered` dönerse araç "hepsi kapalı" demek yerine host'a
ulaşılamadığını belirten bir not ekliyor.

## Banner okuma

SSH, SMTP ve FTP gibi servisler bağlantı kurulduğunda kendini tanıtan bir
satır gönderir; bu satırı okumak yeterlidir. HTTP ise istek bekler; bilinen
web portlarına yalnızca `HEAD /` isteği gönderiliyor. Okunan metin bir eşleme
tablosuyla ürüne çevriliyor (OpenSSH, Postfix, nginx, Redis gibi). Araç hiçbir
koşulda istismar denemesi yapmıyor.

Banner metni ekrana yazılmadan önce kontrol karakterlerinden arındırılıyor.
Ham metin doğrudan terminale basılsaydı, ANSI kaçış dizileri gönderen bir
sunucu terminal çıktısını ve log dosyasını değiştirebilirdi.

## Kapsam kapısı

İzinsiz port taraması Türk Ceza Kanunu kapsamında suç teşkil edebilir. Bu
nedenle kural yalnızca README'de bir uyarı olarak bırakılmadı, koda
yerleştirildi: **varsayılan yapılandırmada internetteki hiçbir hedef
taranamıyor.**

Bir hedefin taranabilmesi için şu koşullardan biri sağlanmalı:

1. Hedefin adı izin listesinde (`SCAN_ALLOWLIST`) olmalı.
2. Hedef yerel ya da özel bir IP adresine çözülmeli.
3. `SCAN_ALLOW_PUBLIC=true` olarak bilinçli şekilde açılmış olmalı.

Kontrol hem alan adı hem çözülen IP üzerinden yapılıyor. Kapı tarama
motorunun önünde duruyor; komut satırı ve REST API aynı servis katmanından
geçtiği için API'ye doğrudan istek gönderen biri de aynı kontrolle
karşılaşıyor. Kapsam dışı hedef komut satırında 3 çıkış koduyla, API'de 403
ile reddediliyor.

## Bilinçli olarak eklenmeyenler

- **SYN taraması:** Ham soket ve yönetici yetkisi gerektirir.
- **UDP taraması:** Anlamlı sonuç için servise özel paketler gerekir.
- **TLS el sıkışması:** 443 açık görünür, sertifika bilgisi okunmaz.
- **Zamanlama profilleri:** nmap'teki `-T0` gibi tespit atlatmaya yönelik
  profiller eklenmedi.

Proje 38 testle birlikte geliyor. Sonuçlar SQLite ya da PostgreSQL'e
kaydediliyor ve geçmiş taramalar `python -m cli list` ile listelenebiliyor.
