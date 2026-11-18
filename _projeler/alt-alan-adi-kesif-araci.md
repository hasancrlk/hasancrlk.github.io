---
title: "Hız mı, nezaket mi? Alt alan adı keşfinde sessiz eksik sonuç tuzağı"
kisa: Bir alan adının altındaki alt alan adlarını DNS ile bulan, hızı sınırlayan ve wildcard sahte sonuçlarını eleyen araç.
ozet: "Bir alan adının altındaki admin., vpn., test. gibi alt alan adlarını bulan bir araç yazdım. En ilginç sorun beklemediğim yerden çıktı: araç fazla hızlıysa hata vermiyor, sessizce eksik sonuç veriyor."
date: 2026-09-18
teknolojiler: [Python, asyncio, dnspython, FastAPI, SQLAlchemy, Docker]
repo: https://github.com/hasancrlk/alt-alan-adi-kesif-araci
kategori: guvenlik
sira: 5
ref: subhound
---

## Problem

Bir kurumun yalnızca `sirket.com` adresi yoktur. Zamanla `admin.sirket.com`,
`vpn.sirket.com`, `test.sirket.com` gibi onlarca alt alan adı birikir ve bir
kısmı unutulur. Kimsenin güncellemediği bir test sunucusu internete açık
kalır. Saldırganların keşif aşaması tam olarak bu adları bulmakla başlar.
Savunan taraf da aynı listeyi kendisi çıkarmalı.

Yöntem basit: 300'den fazla yaygın etiketi (`admin`, `api`, `mail`…)
`<etiket>.sirket.com` hâline getirip DNS'e sormak.

```
$ python -m cli enumerate example.com
Denenen      : 315
Bulunan      : 4 aktif (12 wildcard elendi)
   api.example.com      A       93.184.216.35
*  admin.example.com    A       93.184.216.36
   mail.example.com     CNAME   ghs.googlehosted.com
```

## Zor kısım: İki ayrı ayar

Binlerce DNS sorgusunu hem hızlı yürütmek hem çözümleyiciyi boğmamak
gerekiyor. Kilit nokta bunun **iki ayrı** soru olduğunu görmekti:

| Soru | Araç | Varsayılan |
|---|---|---|
| Aynı anda kaç sorgu uçsun? | `asyncio.Semaphore` | 50 |
| Saniyede kaç sorgu geçsin? | Token bucket | 100/sn |

Yalnızca eşzamanlılığı sınırlamak yetmiyor. 50 eşzamanlı sorgunun her biri 5 ms
sürerse saniyede 10.000 sorgu eder. Çoğu açık DNS çözümleyicisi bu hızda sizi
kısıtlar ve **kısıtlama sessizdir**. `SERVFAIL` ya da `REFUSED` dönen sorgular
kodda "bulunamadı" gibi görünür. Tarama biter, liste kısa çıkar ve kimse bir
şeyin ters gittiğini anlamaz. Hata veren bir araç, sessizce eksik sonuç veren
araçtan çok daha az tehlikeli.

### Neden token bucket?

`sleep(1/hız)` ile sabit aralıklı beklemek basit ama katı. Token bucket kısa
patlamalara izin veriyor ve uzun vadede ortalamayı koruyor. Çözümleyiciler de
tipik olarak saniyelik ortalamaya baktığı için DNS'e uygun davranış bu.

```python
self._tokens = min(capacity, self._tokens + gecen_sure * rate)
```

Bekleme kilidin **dışında** yapılıyor. Kilidi tutarak beklemek, tek bir yavaş
görevin bütün kuyruğu durdurması demekti.

## Wildcard DNS: 300 sahte "bulundu"

Bazı alan adları `*.sirket.com` için bir kayıt tanımlar. Böyle bir alanda
**her** sorgu cevap döner. Bunu fark etmeyen araç 300 satırlık listeden 300
"bulundu" üretir ve hepsi çöptür.

```
1. Rastgele 3 isim sorulur:  subhound-<16 hex>.sirket.com
2. Hepsi cevap veriyorsa     → wildcard var, dönen IP kümesi kaydedilir
3. Biri bile boşsa           → wildcard yok
4. IP kümesi birebir aynı olan bulgular işaretlenir
```

İki karar bilinçli:

- **Neden birebir eşleşme?** Gerçek bir alt alan adı wildcard ile aynı
  sunucuda durabilir, örneğin aynı ters vekilin arkasında. Kısmi eşleşmeyle
  elemek gerçek bulguları kaybettirirdi.
- **Neden silmek yerine işaretlemek?** Elenen kayıt atılmıyor,
  `is_wildcard` ile damgalanıyor. `--show-wildcard` ile görülebiliyor.
  "Şunu buldum ama eledim, istersen bak" demek sessizce atmaktan iyi.

## Fark raporu

Aynı alan adı yeniden tarandığında bir önceki taramada olmayan alt alan adları
`*` ile işaretleniyor. Bunu düzenli çalıştıran bir ekip, birinin unutup açık
bıraktığı yeni bir sunucuyu ilk gün görür.

## Bilerek yapmadıklarım

Gerçek bir keşifte Certificate Transparency kayıtları ve pasif DNS,
kelime listesinden daha verimli. Bunları eklemedim. Zone transfer (`AXFR`)
denemesi bazı araçlarda var ama izin sınırına yakın durduğu için **bilerek**
eklemedim. Alt alan devralma (subdomain takeover) kontrolü de yok.

## Öğrendiklerim

En değerli ders: bir aracın en tehlikeli hata biçimi sessiz eksikliktir.
Çöken program fark edilir. Eksik liste veren program güven verir ve yanıltır.
Hız sınırı bir "nezaket" özelliği gibi görünüyordu, aslında doğruluk özelliği
çıktı.
