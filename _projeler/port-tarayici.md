---
title: "nmap kullanıyordum, sonra kendi port tarayıcımı yazdım"
kisa: Açık TCP portlarını eşzamanlı tarayıp arkadaki servisi banner'dan tahmin eden, izinsiz hedefi reddeden tarayıcı.
ozet: "nmap'i daha önce kullanmıştım: komutu yazar, çıktıyı okurdum. Aynı işi kendi kodumla yazınca o çıktıdaki her kelimenin arkasında ne olduğunu gördüm."
date: 2026-09-18
teknolojiler: [Python, asyncio, FastAPI, SQLAlchemy, argparse, Docker]
repo: https://github.com/hasancrlk/port-tarayici
kategori: guvenlik
sira: 4
ref: portscout
---

PortScout'u nmap'in yerini alsın diye yazmadım. Amacım onun en çok kullanılan
kısmını, yani TCP connect taramasını ve servislerin kendini tanıttığı ilk
satırı (banner) okumayı sıfırdan yazıp nasıl çalıştığını anlamaktı.

```
$ python -m cli scan 127.0.0.1 -p top100
PORT    DURUM     SERVIS     URUN / BANNER
22      open      ssh        OpenSSH/SSH: OpenSSH_9.6
```

## Neden threading değil de asyncio?

Port taraması aslında büyük ölçüde beklemekten ibaret. Her bağlantı ya el
sıkışmayı tamamlıyor ya da zaman aşımı dolana kadar cevap bekliyor; işlemci
bu sürede neredeyse hiçbir şey yapmıyor. Bu yüzden `asyncio` seçtim.

Kararı asıl belirleyen şey zaman aşımının nasıl ele alındığıydı. Bir thread
havuzunda `future.result(timeout=...)` beklemeyi bırakıyor ama iş parçacığını
serbest bırakmıyor; bağlantı işletim sistemi tarafından kapatılana kadar
havuzda yer tutmaya devam ediyor. Cevap vermeyen bir hostta havuz çabucak
doluyor. `asyncio.wait_for` ise coroutine'i iptal ediyor ve yer hemen
boşalıyor.

Eşzamanlılığı da sınırsız bırakmadım. `asyncio.Semaphore` olmadan binlerce
bağlantı aynı anda açılmaya çalışır: sizin tarafınızda dosya tanıtıcısı
sınırına takılır, karşı tarafta da bir SYN selini andırır. Yani araç kazara
bir saldırıya dönüşebilir. Varsayılanı 200 eşzamanlı bağlantı yaptım,
`--concurrency` ile değiştirilebiliyor.

Kaba bir ölçüm vereyim: cevap vermeyen bir hostta 1.000 port, 1 saniye zaman
aşımı ve 200 eşzamanlı bağlantıyla tarama 5 saniye civarında bitiyor.

## Açık değilse kapalı mı?

Değil. Tarayıcı her port için üç durumdan birini veriyor:

- **open:** El sıkışma tamamlandı, port dinleniyor.
- **closed:** Karşı taraf `RST` gönderdi. Host ayakta ama bu portta servis
  yok.
- **filtered:** Hiç cevap gelmedi. Arada bir güvenlik duvarı olabilir ya da
  host kapalı olabilir.

Bütün portlar `filtered` dönerse araç "hepsi kapalı" demek yerine host'a
ulaşılamadığını söyleyen bir not ekliyor. Keşif sırasında bu fark önemli.

## Servisi tanımak

SSH, SMTP ve FTP gibi servisler bağlantı kurulur kurulmaz kendini tanıtan bir
satır gönderiyor; okumak yetiyor. HTTP ise önce istek bekliyor, bu yüzden
bilinen web portlarına yalnızca `HEAD /` gönderiyorum. Okunan metni bir eşleme
tablosuyla ürüne çeviriyorum: OpenSSH, Postfix, nginx, Redis gibi. Araç
hiçbir koşulda istismar denemesi yapmıyor.

Banner'ı ekrana yazmadan önce kontrol karakterlerinden temizliyorum. Ham
metni doğrudan terminale bassaydım, ANSI kaçış dizileri gönderen bir sunucu
terminal çıktınızı ve log dosyanızı değiştirebilirdi.

## İzinsiz taramaya kod içinde engel

İzinsiz port taraması suç teşkil edebilir. Bunu README'ye bir uyarı olarak
yazıp geçmek istemedim, koda koydum: **varsayılan ayarlarla internetteki
hiçbir hedef taranamıyor.** Bir hedefin taranabilmesi için ya adının izin
listesinde (`SCAN_ALLOWLIST`) olması, ya yerel veya özel bir IP adresine
çözülmesi, ya da `SCAN_ALLOW_PUBLIC=true` ayarının bilerek açılmış olması
gerekiyor.

Kontrolü hem alan adı hem de çözülen IP üzerinden yapıyorum; yalnızca ada
bakmak, iç ağdaki bir IP'ye çözülen bir alan adıyla aşılabilirdi. Kapı tarama
motorunun önünde duruyor. Komut satırı ve REST API aynı servis katmanından
geçtiği için API'ye doğrudan istek atan biri de aynı kontrole takılıyor.

## Eklemediklerim

SYN taraması ham soket ve yönetici yetkisi istediği için yok. UDP taraması ve
TLS el sıkışması da yok. nmap'teki `-T0` gibi tespit sistemlerini atlatmaya
yönelik zamanlama profillerini ise bilerek eklemedim.

Proje 38 testle geliyor. Sonuçlar SQLite ya da PostgreSQL'e kaydediliyor ve
geçmiş taramaları `python -m cli list` ile görebiliyorsunuz.
