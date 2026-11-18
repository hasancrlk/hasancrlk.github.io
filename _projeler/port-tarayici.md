---
title: "Neden threading değil asyncio? Sıfırdan eşzamanlı port tarayıcı"
kisa: Açık TCP portlarını eşzamanlı tarayıp arkadaki servisi banner'dan tahmin eden, izinsiz hedefi reddeden tarayıcı.
ozet: "nmap'in en çok kullanılan bir dilimini, yani TCP connect taramasını ve banner okumayı, kendi kodumla yazdım. Yazının konusu iki karar: neden asyncio ve araç kendini kötüye kullanıma karşı nasıl korur."
date: 2026-09-18
teknolojiler: [Python, asyncio, FastAPI, SQLAlchemy, argparse, Docker]
repo: https://github.com/hasancrlk/port-tarayici
kategori: guvenlik
sira: 4
ref: portscout
---

## Problem

Bir sunucudaki her servis bir port üzerinden dinler: SSH 22'den, web 80 ve
443'ten, PostgreSQL 5432'den. Gereksiz yere açık kalmış bir port içeri girmek
için bir kapı demek. Port tarayıcı bu kapıları bulur. Amacım `nmap`'in yerini
almak değildi. Onun en sık kullanılan kısmını sıfırdan yazıp nasıl çalıştığını
gerçekten anlamaktı.

```
$ python -m cli scan 127.0.0.1 -p top100
PORT    DURUM     SERVIS     URUN / BANNER
--------------------------------------------------------------
22      open      ssh        OpenSSH/SSH: OpenSSH_9.6
```

## Karar 1: Neden asyncio?

Port taraması neredeyse tamamen **bekleme** işi. Açılan soket ya el sıkışır ya
da zaman aşımı dolana kadar boşta durur. İşlemci neredeyse hiç çalışmaz.

| | Thread havuzu | asyncio |
|---|---|---|
| Görev başına maliyet | ~1 MB yığın | ~1 KB |
| 5.000 port | Havuz 50–200'de kalır | 5.000 coroutine sorunsuz |
| Zaman aşımı | `future.result(timeout=)` thread'i **bırakmaz** | `asyncio.wait_for` görevi gerçekten iptal eder |

Son satır belirleyici oldu. Thread havuzunda zaman aşımına düşen bir bağlantı,
işletim sistemi soketi kapatana kadar havuzda bir yeri işgal etmeye devam
eder. Cevap vermeyen (filtrelenmiş) bir hostta bu, havuzun tamamen tıkanması
demek ve taramada en sık karşılaşılan durum tam olarak bu. `asyncio.wait_for`
ise coroutine'i iptal ediyor ve yer anında boşalıyor.

Kaba bir ölçüm: cevap vermeyen bir hostta 1.000 port, 1 sn zaman aşımı ve 200
eşzamanlı bağlantıyla yaklaşık **5 saniye**. Seri olarak yaklaşık 1.000
saniye sürerdi.

**Neden sınırsız değil?** `Semaphore` olmadan 65.535 bağlantı aynı anda
başlar. Yerelde `too many open files` hatası alırsınız. Karşı tarafta ise bu
bir SYN selini andırır, yani araç kazara bir hizmet engelleme saldırısına
dönüşür. Varsayılan 200 eşzamanlı bağlantı.

## Üç durum: open, closed, filtered

Basit tarayıcılar "açık değilse kapalı" der. Bu bilgi kaybı:

| Durum | Ne oldu | Anlamı |
|---|---|---|
| open | El sıkışma tamamlandı | Port dinleniyor |
| closed | `RST` geldi | **Host ayakta**, o portta servis yok |
| filtered | Hiç cevap yok | Arada güvenlik duvarı var ya da host kapalı |

Bir hostun bütün portları `filtered` dönüyorsa araç "hepsi kapalı" demiyor,
"host'a ulaşılamadı" notu düşüyor.

## Banner okuma

SSH, SMTP ve FTP gibi servisler bağlantı kurulur kurulmaz kendini tanıtan bir
satır gönderir. Yalnızca okumak yeterli. HTTP ise önce istek bekler, bu yüzden
bilinen web portlarına küçük bir `HEAD /` isteği gidiyor. Gönderilen tek şey
bu. Araç hiçbir zaman istismar denemesi yapmıyor.

Gözden kaçabilecek bir ayrıntı: banner ekrana basılmadan önce **kontrol
karakterlerinden temizleniyor**. Ham banner'ı terminale yazmak, ANSI kaçış
dizileri gönderen kötü niyetli bir sunucunun terminal çıktınızı ve log
dosyanızı değiştirebilmesi demek.

## Karar 2: Araç kendini nasıl korur?

İzinsiz port taraması Türkiye'de suç olabilir. Bunu README'ye yazıp geçmek
yerine koda koydum: **varsayılan ayarda internetteki hiçbir hedef
taranamıyor.**

```
hedef → IP'ye çözümle
  ├─ ad izin listesinde mi?      ─┐
  ├─ IP yerel/özel ağda mı?      ─┼─ evet → TARA
  └─ SCAN_ALLOW_PUBLIC=true mu?  ─┘
                         hayır → 403 / çıkış kodu 3
```

Üç ayrıntı bilinçli:

1. **Hem ad hem IP kontrol ediliyor.** Yalnızca ada bakmak, iç ağdaki bir
   IP'ye çözülen bir alan adıyla atlatılabilirdi.
2. **Kapı tarama motorunun önünde.** CLI de API de aynı servis katmanından
   geçiyor. `curl` ile doğrudan API çağrılsa da aynı denetim çalışıyor.
3. **Açmak bilinçli bir eylem.** `.env` dosyasında yanındaki yorum yazılı
   izin hatırlatması yapıyor.

## Bilerek yapmadıklarım

Yalnızca TCP connect taraması var. SYN taraması yönetici yetkisi ister ve
connect taraması hedefin loglarına tam bağlantı olarak düşer, yani gürültülü.
UDP yok, TLS el sıkışması yok. `nmap -T0` gibi saldırı tespit sistemlerinden
kaçma profillerini **bilerek** eklemedim.

## Öğrendiklerim

"Neden asyncio?" sorusunun cevabını tablodan değil zaman aşımı davranışından
öğrendim. İkinci büyük ders: bir saldırı aracının etik sınırı belgede değil
kodda durmalı. Kullanıcı README okumaz ama kapıya takılır.
