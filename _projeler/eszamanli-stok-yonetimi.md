---
title: "Race Condition ve Stok Yönetimi: 50 Ürün, 300 İstek, Tek Bir SQL Sorgusu"
kisa: Yüzlerce concurrent satın alma isteği altında stoğun asla negatife düşmediğini testle kanıtlayan bir backend servisi.
ozet: "Stokta 50 ürün varken aynı anda 300 satın alma isteği gelirse, yanlış yazılmış bir kod 50'den fazla satış yapabilir. Bu bir race condition; çözümü de uygulama kodunda değil, veritabanında."
date: 2026-08-31
teknolojiler: [Python, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, pytest]
repo: https://github.com/hasancrlk/Es_Zamanlilik_Stok_Yonetimi
kategori: backend
sira: 7
ref: stok
---

Senaryo bir flash sale: stokta 50 oyun konsolu var ve kampanya başladığı anda
yüzlerce kullanıcı aynı anda "Satın Al" isteği gönderiyor. Sistemden iki şey
bekleniyor: overselling olmayacak, yani stoktan fazla satış yapılmayacak, ve
sistem yük altında kilitlenmeyecek.

Bu, EMT Cyber stajında aldığım ilk ödevdi. Bu yazıda problemin kaynağını, tek bir
atomik SQL sorgusuyla nasıl çözdüğümü ve bunu bir concurrency testiyle nasıl
kanıtladığımı anlatıyorum.

## Problem: read-then-write

İlk akla gelen yaklaşım stoğu okumak, yeterli mi diye bakmak ve sonra azaltmak:

```python
urun = await db.get(Item, item_id)
if urun.stock >= adet:
    urun.stock -= adet
```

Tek bir istek için bu kod doğru çalışır. İki istek ilk satırı aynı anda
çalıştırırsa ikisi de aynı stok değerini okur ve ikisi de satışı tamamlar. Buna
**lost update** denir ve sonuç negatif stoktur. Bu tür race condition'lar
yalnızca gerçekten concurrent isteklerde ortaya çıktığı için, istekleri tek tek
göndererek yapılan denemelerde görünmez.

## Çözüm: atomik UPDATE

Kontrol ve azaltmayı tek bir SQL sorgusunda birleştirdim:

```python
result = await db.execute(
    update(Item)
    .where(Item.id == item_id, Item.stock >= body.quantity)
    .values(stock=Item.stock - body.quantity)
    .returning(Item.stock)
)
new_stock = result.scalar_one_or_none()
```

Bu sorgu çalışırken PostgreSQL ilgili satıra bir **row-level lock** koyuyor. Aynı
satıra gelen diğer istekler transaction tamamlanana kadar bekliyor ve sıra
kendilerine geldiğinde `stock >= adet` koşulunu güncel değerle yeniden
değerlendiriyor. Stok yetmiyorsa hiçbir satır güncellenmiyor; servis bu durumda
ürün yoksa `404`, stok bittiyse `409` dönüyor.

Bu yaklaşımla ek bir `SELECT ... FOR UPDATE`, uygulama tarafında lock ya da retry
mekanizmasına gerek kalmıyor; locking işi veritabanına bırakılıyor.

Son savunma hattı olarak tabloda bir `CHECK (stock >= 0)` constraint'i var. Kod
ileride yanlışlıkla değiştirilse bile veritabanı negatif stoğu kabul etmiyor.

## Kanıt: concurrency testi

Bu davranış ancak concurrent istek gönderen bir testle doğrulanabilir; istekleri
tek tek gönderen bir test yanlış kodla da geçer:

```python
async def test_concurrent_purchases_never_go_negative(client):
    stock = 50
    concurrent_requests = 300
    item_id = await _create_item(stock=stock)

    responses = await asyncio.gather(
        *[client.post(f"/purchase/{item_id}") for _ in range(concurrent_requests)]
    )
    status_codes = [r.status_code for r in responses]

    assert status_codes.count(201) == stock
    assert status_codes.count(409) == concurrent_requests - stock
```

Beklenen sonuç tam 50 başarılı satış (`201`), 250 reddedilen istek (`409`) ve
veritabanında 0 stok. Test bilinçli olarak gerçek bir PostgreSQL üzerinde
çalışıyor; row-level lock davranışı SQLite ile test edilemez.

## Neden async?

Bu workload I/O-bound: zamanın büyük kısmı veritabanı cevabını beklemekle
geçiyor. Senkron bir yapıda bekleyen her istek bir worker thread'i meşgul eder
ve thread pool kısa sürede tükenir. Async SQLAlchemy ve asyncpg ile tek bir event
loop, bir istek beklerken diğerlerini işlemeye devam ediyor. Kısa süreli ani yük
senaryoları için uygun model bu.

## Kapanış

Proje yalnızca concurrency problemine odaklanıyor; authentication ve ödeme adımı
yok. Gerçek bir sistemde stok önce reserve edilir, ödeme tamamlanmazsa serbest
bırakılır. Tablolar uygulama açılışında oluşturuluyor; schema değişiklikleri için
Alembic gibi bir migration aracı eklenmesi gerekir.

Race condition'ları "dikkatli kod yazarak" çözmeye çalışmak yerine işi
veritabanına bırakmak, hem daha basit hem daha güvenilir bir sonuç veriyor.
