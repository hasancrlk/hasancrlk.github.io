---
title: "Alt alan adı keşfinde hız sınırı ve wildcard DNS"
kisa: Bir alan adının altındaki alt alan adlarını DNS ile bulan, hızı sınırlayan ve wildcard sahte sonuçlarını eleyen araç.
ozet: "Bir alan adının altındaki admin., vpn., test. gibi alt alan adlarını DNS sorgularıyla bulan bir araç. Yazının odağında iki konu var: hız sınırının sonuçların doğruluğunu nasıl etkilediği ve wildcard DNS'in ürettiği sahte sonuçlar."
date: 2026-09-18
teknolojiler: [Python, asyncio, dnspython, FastAPI, SQLAlchemy, Docker]
repo: https://github.com/hasancrlk/alt-alan-adi-kesif-araci
kategori: guvenlik
sira: 5
ref: subhound
---

Wildcard DNS kaydıyla ilk olarak Bilgisayar Ağları dersinde tanıştım. O
zaman bir yapılandırma ayrıntısı gibi görünüyordu. Bu projede, bir keşif
aracının sonuçlarını tamamen anlamsız hâle getirebilecek bir etken olarak
karşıma çıktı.

## Aracın amacı

Kurumların ana alan adının altında zamanla çok sayıda alt alan adı birikir:
`admin.`, `vpn.`, `test.`, `api.` gibi. Bunların bir kısmı unutulur ve
güncellenmeyen sunucular erişilebilir kalır. Saldırı yüzeyinin çıkarılması bu
adların bulunmasıyla başlar. Bug bounty programlarında ve CTF'lerde de keşif
aşamasının ilk adımı genellikle budur.

Araç, gömülü listedeki 300'den fazla yaygın etiketi `<etiket>.alanadi.com`
biçimine getirip A, AAAA ve CNAME kayıtlarını sorguluyor:

```
$ python -m cli enumerate example.com
Denenen      : 315
Bulunan      : 4 aktif (12 wildcard elendi)
   api.example.com      A       93.184.216.35
*  admin.example.com    A       93.184.216.36
   mail.example.com     CNAME   ghs.googlehosted.com
   www.example.com      A       93.184.216.34
```

## Hız sınırı neden doğrulukla ilgili

Binlerce sorgunun hızlı yürütülmesi için `asyncio` kullanılıyor. Burada iki
ayrı ayar var:

- **Eşzamanlılık:** Aynı anda kaç sorgunun beklemede olacağı.
  `asyncio.Semaphore` ile sınırlanıyor, varsayılan 50.
- **Hız:** Saniyede kaç sorgunun gönderileceği. Token bucket ile
  sınırlanıyor, varsayılan saniyede 100.

Yalnızca eşzamanlılığı sınırlamak yetmiyor. 50 sorgunun her biri birkaç
milisaniye sürerse saniyedeki sorgu sayısı binlerce olur. Açık DNS
çözümleyicilerinin çoğu bu hızda istemciyi kısıtlar ve bunu hata vererek
değil, `SERVFAIL` ya da `REFUSED` döndürerek yapar. Kodda bu cevaplar "kayıt
bulunamadı" ile aynı görünür. Sonuç olarak tarama hatasız tamamlanır ama
liste eksik çıkar.

Token bucket, sabit aralıklı beklemeye göre kısa ani yüklere izin verirken
uzun vadeli ortalamayı korur. Bekleme işlemi kilidin dışında yapılıyor;
böylece yavaş bir görev kuyruğun tamamını durdurmuyor.

```python
self._tokens = min(capacity, self._tokens + gecen_sure * rate)
```

## Wildcard DNS

Bir alan adı `*.example.com` için kayıt tanımlamışsa, var olmayan her isim de
cevap döner. Bunu fark etmeyen bir araç listedeki her kelime için "bulundu"
raporlar.

Araç taramaya başlamadan önce rastgele üretilmiş üç isim sorguluyor
(`subhound-<16 hex>.example.com`). Üçü de cevap veriyorsa alanda wildcard
olduğu kabul ediliyor ve dönen IP kümesi kaydediliyor. Taramada IP kümesi bu
kümeyle **birebir** aynı olan sonuçlar wildcard olarak işaretleniyor.

Kısmi eşleşme yerine birebir eşleşme kullanılmasının nedeni, gerçek bir alt
alan adının wildcard ile aynı sunucuda barınabilmesi. Elenen sonuçlar
silinmiyor, `is_wildcard` olarak işaretleniyor ve `--show-wildcard` ile
görüntülenebiliyor.

## Fark raporu

Aynı alan adı tekrar tarandığında önceki taramada olmayan alt alan adları `*`
ile işaretleniyor. Düzenli çalıştırıldığında yeni açılan bir sunucunun
fark edilmesini kolaylaştırıyor.

## Kapsam ve sınırlar

Keşif yalnızca size ait ya da test izni verilmiş alan adlarında yapılmalıdır.
Araç bu nedenle varsayılan olarak hız sınırlı çalışıyor.

Gerçek bir keşifte Certificate Transparency kayıtları ve pasif DNS
kaynakları kelime listesinden daha verimlidir; bu kaynaklar eklenmedi. Zone
transfer (`AXFR`) denemesi izin sınırına yakın olduğu için bilinçli olarak
dışarıda bırakıldı. Alt alan devralma (subdomain takeover) kontrolü ve
Türkçe karakterli alan adları için punycode dönüşümü de bulunmuyor.

Proje 42 testle birlikte geliyor; komut satırı ve REST API aynı motoru
kullanıyor.
