---
title: "Elli ürün, üç yüz istek ve tek bir SQL cümlesi"
kisa: Yüzlerce eşzamanlı satın alma isteği altında stoğun asla eksiye düşmediğini testle kanıtlayan arka uç servisi.
ozet: "Stokta 50 ürün var, aynı saniyede 300 kişi satın almaya çalışıyor. Kaç kişi ürünü alır? Doğru cevap 50. Ama yanlış yazılmış bir kod 51, hatta 60 da diyebilir."
date: 2026-08-31
teknolojiler: [Python, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, pytest]
repo: https://github.com/hasancrlk/Es_Zamanlilik_Stok_Yonetimi
kategori: backend
sira: 7
ref: stok
---

EMT Cyber stajında aldığım ilk ödev buydu. Senaryo bir flaş indirim: stokta 50
oyun konsolu var ve kampanya başladığı anda yüzlerce kişi aynı anda "Satın Al"a
basıyor. Benden istenen iki şey vardı: stoktan fazla satış olmayacak ve sistem
yük altında kilitlenmeyecek.

## Kâğıt üstünde doğru görünen kod

Bu işi yazarken çoğumuzun aklına ilk gelen yöntem şudur:

```python
urun = await db.get(Item, item_id)
if urun.stock >= adet:
    urun.stock -= adet
```

Stoğu oku, yetiyor mu bak, yetiyorsa azalt. Tek bir kullanıcı için kusursuz.
Peki iki istek ilk satırı aynı anda çalıştırırsa ne olur? İkisi de "stokta 1
kaldı" görür, ikisi de satışı tamamlar ve stok `-1` olur. Bunun adı **kayıp
güncelleme** (lost update).

Bu hatayı sinsi yapan şey, tek tek denediğinizde hiçbir zaman ortaya
çıkmaması. Hata ancak gerçekten eşzamanlı istek geldiğinde görünüyor.

## Kontrolü ve azaltmayı tek cümlede yapmak

Çözüm olarak kontrol ile azaltmayı birbirinden ayırmadım, tek bir SQL
cümlesinde birleştirdim:

```python
result = await db.execute(
    update(Item)
    .where(Item.id == item_id, Item.stock >= body.quantity)
    .values(stock=Item.stock - body.quantity)
    .returning(Item.stock)
)
new_stock = result.scalar_one_or_none()
```

Bu cümle çalışırken PostgreSQL ilgili satırı kilitliyor. Aynı ürüne gelen
diğer istekler sırada bekliyor ve sıra kendilerine geldiğinde `stock >= adet`
koşuluna stoğun **o anki** değeriyle yeniden bakıyor. Stok yetmiyorsa hiçbir
satır güncellenmiyor; ben de bu durumda ürün yoksa `404`, stok bittiyse `409`
döndürüyorum.

Yani ek bir `SELECT ... FOR UPDATE` sorgusu, uygulama tarafında kilit ya da
yeniden deneme döngüsü yazmama gerek kalmadı. Kilitleme işini veritabanına
bıraktım.

Bir de tabloya `CHECK (stock >= 0)` kısıtı ekledim. Kodu ileride biri
yanlışlıkla değiştirse bile veritabanı eksi stoğu kabul etmiyor.

## Peki bunun çalıştığını nasıl kanıtlarsınız?

Tek tek istek gönderen bir test burada hiçbir şey kanıtlamaz, çünkü yanlış kod
da o testi geçer. Bu yüzden 300 isteği aynı anda gönderen bir test yazdım:

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

Beklenen sonuç tam 50 başarılı satış, 250 reddedilen istek ve veritabanında 0
stok. Testi bilerek gerçek bir PostgreSQL üzerinde çalıştırıyorum; satır
kilidi davranışını SQLite ile sınamak mümkün değil.

## Neden async?

Bu iş yükünde zamanın neredeyse tamamı veritabanını beklemekle geçiyor.
Senkron yazsaydım bekleyen her istek bir iş parçacığını meşgul edecek ve havuz
kısa sürede dolacaktı. Async SQLAlchemy ve asyncpg ile tek bir olay döngüsü,
bir istek beklerken diğerlerini işlemeye devam ediyor.

## Bilerek dışarıda bıraktıklarım

Ödevin odağı eşzamanlılıktı, o yüzden kimlik doğrulama ve ödeme adımı
eklemedim. Gerçek bir sistemde stok önce rezerve edilir, ödeme tamamlanmazsa
geri bırakılır. Şema değişiklikleri için de Alembic gibi bir migration aracı
eklemek gerekir.
