---
title: "Kendi Port Scanner'ımı Yazmak: asyncio, Banner Grabbing ve Scope Kontrolü"
kisa: TCP portlarını eşzamanlı tarayıp banner'dan servisi tespit eden, izinsiz hedefleri reddeden bir port scanner.
ozet: "Daha önce nmap kullanmıştım; komutu yazar, çıktıyı okurdum. TCP connect scan ve banner grabbing'i kendi kodumla yazınca o çıktıdaki her satırın arkasındaki ağ davranışını görmüş oldum."
date: 2026-09-18
teknolojiler: [Python, asyncio, FastAPI, SQLAlchemy, argparse, Docker]
repo: https://github.com/hasancrlk/port-tarayici
kategori: guvenlik
sira: 4
ref: portscout
---

PortScout'u nmap'in yerini alması için değil, onun en sık kullanılan kısmını
anlamak için yazdım: TCP connect scan ve servislerin bağlantı kurulduğunda
gönderdiği ilk satırın, yani banner'ın okunması. Bu da EMT Cyber stajında verilen
ödevlerden biriydi.

Bu yazıda iki tasarım kararını anlatıyorum: concurrency için neden `asyncio`
seçtiğimi ve aracın kötüye kullanıma karşı kendini nasıl sınırladığını.

```
$ python -m cli scan 127.0.0.1 -p top100
PORT    DURUM     SERVIS     URUN / BANNER
22      open      ssh        OpenSSH/SSH: OpenSSH_9.6
```

## Neden threading değil, asyncio?

Port scanning I/O-bound bir iş: her bağlantı ya TCP handshake'i tamamlıyor ya da
timeout dolana kadar cevap bekliyor. CPU bu sürede neredeyse hiçbir şey yapmıyor.

Kararı belirleyen şey timeout davranışı oldu. Bir thread pool'da
`future.result(timeout=...)` beklemeyi bırakır ama thread'i serbest bırakmaz;
bağlantı OS tarafından kapatılana kadar pool'da bir slot işgal etmeye devam eder.
Cevap vermeyen (filtered) bir host'ta pool hızla tıkanır. `asyncio.wait_for` ise
coroutine'i gerçekten iptal ediyor ve slot hemen boşalıyor.

Concurrency sınırsız da değil. `asyncio.Semaphore` olmadan binlerce bağlantı aynı
anda açılmaya çalışır: lokalde `too many open files` hatasına takılır, karşı
tarafta ise bir SYN flood'u andırır. Varsayılan değer 200 eşzamanlı bağlantı,
`--concurrency` ile değiştirilebiliyor.

Kaba bir ölçüm: cevap vermeyen bir host'ta 1.000 port, 1 saniye timeout ve 200
concurrency ile tarama yaklaşık 5 saniyede bitiyor. Seri olarak yaklaşık 1.000
saniye sürerdi.

## open, closed, filtered

Basit scanner'lar "open değilse closed" der; bu bilgi kaybıdır. PortScout her port
için üç durumdan birini raporluyor:

- **open.** Handshake tamamlandı, port dinleniyor.
- **closed.** Karşı taraf `RST` gönderdi. Host ayakta, ama bu portta servis yok.
- **filtered.** Hiç cevap gelmedi. Arada bir firewall olabilir ya da host kapalı
  olabilir.

Bütün portlar `filtered` dönerse araç "hepsi kapalı" demek yerine host'a
ulaşılamadığını belirten bir not ekliyor.

## Banner grabbing

SSH, SMTP ve FTP gibi servisler bağlantı kurulur kurulmaz bir banner gönderir;
okumak yeterlidir. HTTP ise istek bekler, bu yüzden bilinen web portlarına
yalnızca minimal bir `HEAD /` gönderiliyor. Okunan banner regex tabanlı bir
tabloyla ürüne eşleniyor: OpenSSH, Postfix, nginx, Redis gibi. Araç hiçbir koşulda
exploit denemesi yapmıyor.

Banner terminale yazılmadan önce control karakterlerinden temizleniyor. Ham
banner'ı doğrudan terminale basmak, ANSI escape sequence gönderen kötü niyetli bir
sunucunun terminal çıktısını ve log dosyasını değiştirebilmesi anlamına gelir.

## Scope kontrolü

İzinsiz port taraması suç teşkil edebilir. Bu kuralı README'de bir uyarı olarak
bırakmak yerine koda koydum: **varsayılan config ile internetteki hiçbir hedef
taranamıyor.** Bir hedefin taranabilmesi için şu koşullardan biri sağlanmalı:

- **Allowlist.** Hedefin adı `SCAN_ALLOWLIST` içinde.
- **Private IP.** Hedef loopback ya da private bir IP adresine çözülüyor.
- **Bilinçli açma.** `SCAN_ALLOW_PUBLIC=true` ayarı elle açılmış.

Kontrol hem domain adı hem de çözülen IP üzerinden yapılıyor; yalnızca isme
bakmak, internal bir IP'ye çözülen bir domain ile atlatılabilirdi. Kontrol scan
engine'in önünde duruyor; CLI ve REST API aynı service katmanından geçtiği için
API'ye doğrudan `curl` atan biri de aynı kontrole takılıyor. Kapsam dışı bir hedef
CLI'da exit code 3, API'de 403 ile reddediliyor.

## Kapanış

Bilinçli olarak eklemediğim özellikler var: SYN scan (raw socket ve root yetkisi
ister), UDP scan, TLS handshake ve nmap'teki `-T0` gibi IDS evasion amaçlı timing
profilleri. PortScout bir keşif aracı olarak bilerek "gürültülü" ve sınırlı.

Kendi scanner'ını yazmak, nmap çıktısındaki `filtered` gibi tek kelimelik bir
durumun arkasında hangi ağ davranışının yattığını görmenin en doğrudan yolu.
Proje 38 testle geliyor; sonuçlar SQLite ya da PostgreSQL'e kaydediliyor.

*Bu araç yalnızca sahibi olduğunuz ya da yazılı test izni verilmiş sistemlerde
kullanılmalıdır.*
