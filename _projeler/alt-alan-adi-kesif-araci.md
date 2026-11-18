---
title: "Subdomain Enumeration'da Rate Limit ve Wildcard DNS Sorunu"
kisa: Bir domain altındaki subdomain'leri DNS sorgularıyla bulan, rate limit uygulayan ve wildcard false positive'lerini eleyen bir recon aracı.
ozet: "Bir recon aracının en tehlikeli hatası çökmek değil, hata vermeden eksik sonuç döndürmektir. Subdomain enumeration'da bunun iki kaynağı var: DNS resolver'ların sessiz rate limiting'i ve wildcard DNS."
date: 2026-09-18
teknolojiler: [Python, asyncio, dnspython, FastAPI, SQLAlchemy, Docker]
repo: https://github.com/hasancrlk/alt-alan-adi-kesif-araci
kategori: guvenlik
sira: 5
ref: subhound
---

Bir kurumun ana domain'i altında zamanla `admin.`, `vpn.`, `test.`, `api.` gibi
onlarca subdomain birikir. Bir kısmı unutulur ve güncellenmeyen sunucular
erişilebilir kalır. Attack surface'i çıkarmak bu isimleri bulmakla başlar; bug
bounty programlarında ve CTF'lerde de recon aşamasının ilk adımı genellikle budur.

Wildcard DNS ile ilk olarak Bilgisayar Ağları dersinde tanışmıştım. Bu yazıda
EMT Cyber stajında ödev olarak geliştirdiğim SubHound'u ve bir recon aracını
sessizce yanıltabilecek iki sorunu nasıl ele aldığını anlatıyorum.

```
$ python -m cli enumerate example.com
Denenen      : 315
Bulunan      : 4 aktif (12 wildcard elendi)
   api.example.com      A       93.184.216.35
*  admin.example.com    A       93.184.216.36
   mail.example.com     CNAME   ghs.googlehosted.com
   www.example.com      A       93.184.216.34
```

SubHound wordlist tabanlı çalışıyor: gömülü listedeki 300'den fazla etiketi
`<etiket>.domain.com` hâline getirip A, AAAA ve CNAME kayıtlarını sorguluyor.

## Concurrency ile rate limit aynı şey değil

Binlerce DNS sorgusunu hızlı yürütmek için `asyncio` kullandım. Burada birbirinden
bağımsız iki ayar var:

- **Concurrency.** Aynı anda kaç sorgunun beklemede olacağı. `asyncio.Semaphore`
  ile sınırlanıyor, varsayılan 50.
- **Rate limit.** Saniyede kaç sorgu gönderileceği. Token bucket ile
  sınırlanıyor, varsayılan saniyede 100.

Sadece concurrency'yi sınırlamak yetmiyor. 50 sorgunun her biri birkaç milisaniye
sürerse saniyede binlerce sorgu gider. Çoğu public DNS resolver bu hızda
client'ı kısıtlıyor ve bunu hata vererek değil, `SERVFAIL` ya da `REFUSED`
döndürerek yapıyor. Kodda bu cevaplar "kayıt yok" ile aynı görünüyor. Tarama
hatasız tamamlanıyor, ama liste eksik çıkıyor.

Token bucket'ı sabit aralıklı `sleep`'e tercih ettim: kısa burst'lere izin
verirken uzun vadeli ortalamayı koruyor. Bekleme lock'un dışında yapılıyor;
yavaş bir task bütün kuyruğu durdurmuyor.

```python
self._tokens = min(capacity, self._tokens + gecen_sure * rate)
```

## Wildcard DNS ve false positive'ler

Bir domain `*.example.com` için kayıt tanımlamışsa, var olmayan her isim de cevap
döner. Bunu fark etmeyen bir araç wordlist'teki her kelime için "bulundu" der.

SubHound taramaya başlamadan önce rastgele üretilmiş üç isim sorguluyor
(`subhound-<16 hex>.example.com`). Üçü de cevap veriyorsa domain'de wildcard
olduğu kabul ediliyor ve dönen IP kümesi kaydediliyor. Tarama sırasında IP kümesi
bu kümeyle **birebir** aynı olan sonuçlar wildcard olarak işaretleniyor.

Kısmi değil birebir eşleşme kullanmamın sebebi şu: gerçek bir subdomain de
wildcard ile aynı sunucuda, örneğin aynı reverse proxy'nin arkasında duruyor
olabilir. Elenen sonuçlar silinmiyor, `is_wildcard` olarak işaretleniyor ve
`--show-wildcard` ile görüntülenebiliyor.

## Diff raporu

Aynı domain tekrar tarandığında, önceki taramada olmayan subdomain'ler `*` ile
işaretleniyor. Araç düzenli çalıştırıldığında yeni açılan bir sunucu ilk gün fark
edilebiliyor.

## Kapanış

SubHound'un bilinçli sınırları var. Gerçek bir recon'da Certificate Transparency
log'ları ve passive DNS kaynakları wordlist'ten daha verimli; bunlar eklenmedi.
Zone transfer (`AXFR`) denemesi izin sınırına yakın olduğu için bilerek dışarıda
bırakıldı. Subdomain takeover kontrolü ve IDN/punycode desteği de yok.

Bu projede rate limit'in bir "nezaket" özelliği değil, doğrudan bir doğruluk
özelliği olduğu ortaya çıktı: sessizce kısıtlanan bir tarama, eksik ama güven
veren bir sonuç üretir. Proje 42 testle geliyor; CLI ve REST API aynı engine'i
kullanıyor.

*Recon yalnızca sahibi olduğunuz ya da test izni verilmiş domain'lerde
yapılmalıdır.*
