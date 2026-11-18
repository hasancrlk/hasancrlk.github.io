---
title: "50 konsol, 300 alıcı: flaş indirimde stok neden eksiye düşer, nasıl düşmez?"
kisa: Yüzlerce eşzamanlı satın alma isteği altında stoğun asla eksiye düşmediğini testle kanıtlayan arka uç servisi.
ozet: "Stokta 50 ürün varken aynı anda 300 kişi satın almaya çalışırsa ne olur? Bu sorunun cevabını tek bir SQL cümlesiyle verdim ve bir testle kanıtladım."
date: 2026-08-31
teknolojiler: [Python, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, pytest]
repo: https://github.com/hasancrlk/Es_Zamanlilik_Stok_Yonetimi
kategori: backend
sira: 7
ref: stok
---

## Problem

Bir e-ticaret sitesi flaş indirim yapıyor. Stokta 50 oyun konsolu var ve
kampanya başladığı saniyede yüzlerce kişi "Satın Al"a basıyor. İki şey
olmamalı:

1. **Stoktan fazla satış.** Elinizde olmayan bir ürünü satmak.
2. **Sistemin kilitlenmesi.** Yük altında sitenin cevap verememesi.

Bu küçük servis ürünleri listeliyor ve satın alma isteklerini karşılıyor. Asıl
amacı birinci maddenin nasıl doğru çözüleceğini göstermek.

## Yanlış yol: Önce oku, sonra yaz

İlk akla gelen kod şu:

```python
urun = await db.get(Item, item_id)     # 1. stoğu oku
if urun.stock >= adet:                  # 2. yeterli mi?
    urun.stock -= adet                  # 3. düşür ve kaydet
```

Tek kullanıcıda kusursuz çalışıyor. İki istek 1. adımı aynı anda çalıştırınca
ikisi de "stokta 1 kaldı" görüyor ve ikisi de satışı tamamlıyor. Buna **kayıp
güncelleme** (lost update) deniyor. Sonuç: stok `-1`.

Bu tür hatanın sinsi yanı, geliştirme sırasında neredeyse hiç görünmemesi.
Yerelde tek tek tıklayarak denerken asla çıkmıyor. Ancak gerçek yük altında
ortaya çıkıyor.

## Doğru yol: Tek atomik cümle

Kontrol ile düşürmeyi ayırmak yerine tek bir SQL cümlesinde birleştirdim:

```python
result = await db.execute(
    update(Item)
    .where(Item.id == item_id, Item.stock >= body.quantity)
    .values(stock=Item.stock - body.quantity)
    .returning(Item.stock)
)
new_stock = result.scalar_one_or_none()
```

Bu neden güvenli?

1. PostgreSQL satırı güncellerken o satıra otomatik olarak **satır kilidi**
   koyuyor.
2. Aynı satıra gelen diğer istekler ilk işlem bitene kadar **sırada
   bekliyor**.
3. Sıra kendisine gelen istek `stock >= adet` koşulunu **güncel değerle
   yeniden** değerlendiriyor. Stok yetmiyorsa hiçbir satır güncellenmiyor.
4. Güncellenen satır yoksa servis ürünün var olup olmadığına bakıyor ve buna
   göre `404` ya da `409` dönüyor.

Ek bir `SELECT ... FOR UPDATE` sorgusuna, uygulama tarafında kilide ya da
yeniden deneme döngüsüne gerek kalmıyor.

### Son güvenlik ağı

Tabloda bir veritabanı kısıtı var: `CHECK (stock >= 0)`. Kod bir gün
yanlışlıkla değiştirilse bile veritabanı eksi stoku reddediyor. Kuralın
veritabanında da durması, kod yolu unutulduğunda bile korumanın sürmesini
sağlıyor.

## Kanıt

Bir kuralı "çalışıyor" demek yetmez, testle göstermek lazım:

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
    # ve veritabanındaki son stok tam olarak 0
```

300 isteğin tam 50'si başarılı oluyor, 250'si "stok tükendi" cevabı alıyor ve
son stok 0'da kalıyor. Test gerçek bir PostgreSQL üzerinde çalışıyor, çünkü
satır kilidi davranışı SQLite ile sınanamıyor.

## Neden async?

Bu iş yükünde zamanın büyük kısmı veritabanını beklemekle geçiyor. Senkron
kodda bekleyen her istek bir iş parçacığını meşgul ediyor ve havuz hızla
doluyor. Async SQLAlchemy ve asyncpg ile tek bir olay döngüsü, bir istek
veritabanını beklerken diğerlerini işlemeye devam ediyor. Kısa süreli ani yük
için doğru model bu.

## Bilerek yapmadıklarım

Kimlik doğrulama ve ödeme adımı yok. Gerçek hayatta stok önce rezerve edilir,
ödeme tamamlanmazsa geri bırakılır. Tablolar açılışta oluşturuluyor; şema
değişiklikleri için migration aracı (Alembic) eklenmeli.

## Öğrendiklerim

Eşzamanlılık hatalarını "dikkatli kod yazarak" değil, **işi veritabanına
bırakarak** çözmeyi öğrendim. Veritabanı satır kilidi konusunda benim
yazabileceğim herhangi bir kilitten daha güvenilir. İkinci ders: bu tür bir
garanti ancak eşzamanlı istek gönderen bir testle kanıtlanır. Tek tek istek
gönderen test her zaman geçer.
