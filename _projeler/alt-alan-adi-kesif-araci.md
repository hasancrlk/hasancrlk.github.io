---
title: "Alt alan adı keşfinde hız sınırı ve wildcard DNS"
kisa: Bir alan adının altındaki alt alan adlarını DNS ile bulan, hızı sınırlayan ve wildcard sahte sonuçlarını eleyen araç.
ozet: "Wildcard DNS'i Bilgisayar Ağları dersinde bir yapılandırma ayrıntısı olarak öğrenmiştim. Bir keşif aracı yazınca, aynı ayrıntının bütün sonuçları çöpe çevirebildiğini gördüm."
date: 2026-09-18
teknolojiler: [Python, asyncio, dnspython, FastAPI, SQLAlchemy, Docker]
repo: https://github.com/hasancrlk/alt-alan-adi-kesif-araci
kategori: guvenlik
sira: 5
ref: subhound
---

Bir kurumun ana alan adının altında zamanla `admin.`, `vpn.`, `test.`, `api.`
gibi onlarca alt alan adı birikir. Bir kısmı unutulur ve güncellenmeyen
sunucular erişilebilir kalır. Bug bounty programlarında da, CTF'lerde de
keşfin ilk adımı genellikle bu adları bulmaktır; ben de bu iki alanla
ilgileniyorum.

Araç, içine gömdüğüm 300'den fazla yaygın etiketi `<etiket>.alanadi.com`
hâline getirip A, AAAA ve CNAME kayıtlarını soruyor:

```
$ python -m cli enumerate example.com
Denenen      : 315
Bulunan      : 4 aktif (12 wildcard elendi)
   api.example.com      A       93.184.216.35
*  admin.example.com    A       93.184.216.36
   mail.example.com     CNAME   ghs.googlehosted.com
   www.example.com      A       93.184.216.34
```

## Hızlı olmak neden yanlış sonuç verebilir?

Binlerce sorguyu hızlı yürütmek için `asyncio` kullandım. Burada iki ayrı
ayar var ve ikisini birbirine karıştırmamak gerekiyor:

- **Eşzamanlılık:** Aynı anda kaç sorgunun beklemede olacağı. Bunu
  `asyncio.Semaphore` ile 50'de tuttum.
- **Hız:** Saniyede kaç sorgu gönderileceği. Bunu token bucket ile saniyede
  100'e sınırladım.

Sadece eşzamanlılığı sınırlamak yetmiyor. 50 sorgunun her biri birkaç
milisaniye sürerse saniyede binlerce sorgu gider. Açık DNS
çözümleyicilerinin çoğu bu hızda sizi kısıtlıyor, üstelik bunu hata vererek
değil `SERVFAIL` ya da `REFUSED` döndürerek yapıyor. Kodda bu cevaplar "kayıt
yok" ile aynı görünüyor. Sonuçta tarama hatasız bitiyor ama liste eksik
çıkıyor. Hata vermeden eksik sonuç veren bir araç, hata veren bir araçtan çok
daha tehlikelidir.

Token bucket'ı sabit aralıklı beklemeye tercih ettim çünkü kısa ani yüklere
izin verirken uzun vadede ortalamayı koruyor. Beklemeyi kilidin dışında
yapıyorum; böylece yavaş bir görev bütün kuyruğu durdurmuyor.

```python
self._tokens = min(capacity, self._tokens + gecen_sure * rate)
```

## Her isme cevap veren alan adları

Bir alan adı `*.example.com` için kayıt tanımlamışsa, var olmayan her isim de
cevap döner. Bunu fark etmeyen bir araç listedeki her kelime için "bulundu"
der.

Bu yüzden taramaya başlamadan önce rastgele üç isim soruyorum
(`subhound-<16 hex>.example.com`). Üçü de cevap veriyorsa alanda wildcard
olduğunu kabul edip dönen IP kümesini kaydediyorum. Taramada IP kümesi bu
kümeyle **birebir** aynı olan sonuçları wildcard olarak işaretliyorum.

Kısmi değil birebir eşleşme kullanmamın sebebi şu: gerçek bir alt alan adı da
wildcard ile aynı sunucuda duruyor olabilir. Elenen sonuçları silmiyorum,
`is_wildcard` olarak işaretliyorum; `--show-wildcard` ile görebiliyorsunuz.

## Yeni çıkanı fark etmek

Aynı alan adını tekrar taradığınızda, önceki taramada olmayan alt alan
adları `*` ile işaretleniyor. Düzenli çalıştırırsanız yeni açılan bir sunucuyu
ilk gün fark edersiniz.

## Kapsam ve sınırlar

Keşfi yalnızca size ait ya da test izni verilmiş alan adlarında yapmalısınız.
Aracın varsayılan olarak hız sınırlı çalışmasının bir sebebi de bu.

Gerçek bir keşifte Certificate Transparency kayıtları ve pasif DNS kaynakları
kelime listesinden daha verimli; bunları eklemedim. Zone transfer (`AXFR`)
denemesini ise izin sınırına yakın olduğu için bilerek dışarıda bıraktım. Alt
alan devralma kontrolü ve Türkçe karakterli alan adları için punycode
dönüşümü de yok.

Proje 42 testle geliyor; komut satırı ve REST API aynı motoru kullanıyor.
