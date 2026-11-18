---
title: "Elli ürün, üç yüz istek ve tek bir SQL cümlesi"
kisa: Yüzlerce eşzamanlı satın alma isteği altında stoğun asla eksiye düşmediğini testle kanıtlayan arka uç servisi.
ozet: "Stokta 50 ürün varken aynı anda 300 satın alma isteği gelirse ne olur? Bu servis, sorunun cevabını tek bir atomik SQL cümlesiyle veriyor ve bir eşzamanlılık testiyle kanıtlıyor."
date: 2026-08-31
teknolojiler: [Python, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, pytest]
repo: https://github.com/hasancrlk/Es_Zamanlilik_Stok_Yonetimi
kategori: backend
sira: 7
ref: stok
---

Senaryo bir flaş indirim: stokta 50 oyun konsolu var ve kampanya başladığı
anda çok sayıda kullanıcı aynı anda satın alma isteği gönderiyor. Sistemden
beklenen iki şey var: stoktan fazla satış yapılmaması ve yük altında
sistemin kilitlenmemesi.

Bu proje EMT Cyber stajında verilen ödevlerin ilkiydi.

## Sorunun kaynağı

İlk akla gelen yöntem stoğu okuyup kontrol etmek, sonra azaltmak:

```python
urun = await db.get(Item, item_id)
if urun.stock >= adet:
    urun.stock -= adet
```

Tek bir istek için bu kod doğru çalışır. İki istek ilk satırı aynı anda
çalıştırırsa ikisi de aynı stok değerini okur ve ikisi de satışı tamamlar.
Bu duruma **kayıp güncelleme** (lost update) denir ve sonuç eksi stoktur. Hata
yalnızca eşzamanlı isteklerde ortaya çıktığı için tek tek yapılan denemelerde
görünmez.

## Çözüm

Kontrol ve azaltma tek bir SQL cümlesinde birleştirildi:

```python
result = await db.execute(
    update(Item)
    .where(Item.id == item_id, Item.stock >= body.quantity)
    .values(stock=Item.stock - body.quantity)
    .returning(Item.stock)
)
new_stock = result.scalar_one_or_none()
```

PostgreSQL bu cümleyi çalıştırırken ilgili satıra satır kilidi koyar. Aynı
satıra gelen diğer istekler ilk işlem tamamlanana kadar bekler ve sıra
kendilerine geldiğinde `stock >= adet` koşulunu güncel değer üzerinden yeniden
değerlendirir. Stok yetersizse hiçbir satır güncellenmez. Bu durumda servis
ürünün var olup olmadığına bakıp `404` ya da `409` döner.

Bu yaklaşımla ek bir `SELECT ... FOR UPDATE` sorgusuna, uygulama tarafında
kilide ya da yeniden deneme döngüsüne ihtiyaç kalmıyor.

Ayrıca tabloda `CHECK (stock >= 0)` kısıtı tanımlı. Kod ileride yanlışlıkla
değiştirilse bile veritabanı eksi stoğu kabul etmiyor.

## Doğrulama

Bu davranış ancak eşzamanlı istek gönderen bir testle doğrulanabilir; tek tek
gönderilen isteklerle yazılmış bir test her koşulda geçer:

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

Test 300 isteği aynı anda gönderiyor. Beklenen sonuç tam 50 başarılı satış
(`201`), 250 reddedilen istek (`409`) ve veritabanında 0 stok. Test gerçek bir
PostgreSQL üzerinde çalışıyor; satır kilidi davranışı SQLite ile
sınanamadığı için bu bilinçli bir tercih.

## Asenkron yapı

Bu iş yükünde zamanın büyük bölümü veritabanı cevabını beklemekle geçiyor.
Senkron bir yapıda bekleyen her istek bir iş parçacığını meşgul eder ve havuz
kısa sürede dolar. Async SQLAlchemy ve asyncpg ile tek bir olay döngüsü, bir
istek beklerken diğerlerini işlemeye devam ediyor. Kısa süreli ani yük
senaryoları için uygun model bu.

## Kapsam

Proje yalnızca eşzamanlılık sorununa odaklanıyor. Kimlik doğrulama ve ödeme
adımı yok; gerçek bir sistemde stok önce rezerve edilir, ödeme tamamlanmazsa
serbest bırakılır. Tablolar uygulama açılışında oluşturuluyor; şema
değişiklikleri için Alembic gibi bir migration aracı eklenmesi gerekir.
