---
title: "Fifty items, three hundred requests and a single SQL statement"
kisa: A backend service that proves, with a test, that stock never goes negative under hundreds of concurrent purchases.
ozet: "What happens when 300 purchase requests arrive at once and only 50 items are in stock? This service answers with a single atomic SQL statement and proves it with a concurrency test."
date: 2026-08-31
teknolojiler: [Python, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, pytest]
repo: https://github.com/hasancrlk/Es_Zamanlilik_Stok_Yonetimi
kategori: backend
sira: 7
ref: stok
---

The scenario is a flash sale: 50 game consoles are in stock, and the moment
the campaign starts, many users send purchase requests at the same time. Two
things are expected of the system: no overselling, and no lock-up under load.

This was the first of the assignments given during my internship at EMT Cyber.

## Where the problem comes from

The first approach that comes to mind is to read the stock, check it, then
decrement it:

```python
item = await db.get(Item, item_id)
if item.stock >= qty:
    item.stock -= qty
```

For a single request this code is correct. If two requests run the first line
at the same time, both read the same stock value and both complete the sale.
This is a **lost update**, and the result is negative stock. Because the bug
only appears with concurrent requests, it does not show up when testing one
request at a time.

## The fix

The check and the decrement were merged into one SQL statement:

```python
result = await db.execute(
    update(Item)
    .where(Item.id == item_id, Item.stock >= body.quantity)
    .values(stock=Item.stock - body.quantity)
    .returning(Item.stock)
)
new_stock = result.scalar_one_or_none()
```

When PostgreSQL executes this statement it puts a row lock on the row. Other
requests for the same row wait until the first transaction completes, and
when their turn comes they re-evaluate `stock >= qty` against the current
value. If there is not enough stock, no row is updated, and the service checks
whether the product exists to return `404` or `409`.

With this approach there is no need for an extra `SELECT ... FOR UPDATE`, an
application-level lock or a retry loop.

The table also has a `CHECK (stock >= 0)` constraint. Even if the code is
changed by mistake later, the database will not accept negative stock.

## Verification

This behaviour can only be verified with a test that sends concurrent
requests; a test that sends them one by one passes in every case:

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

The test sends 300 requests at once. The expected result is exactly 50
successful sales (`201`), 250 rejected requests (`409`) and 0 stock in the
database. The test runs against a real PostgreSQL instance; row-lock
behaviour can't be tested with SQLite, so this is a deliberate choice.

## The asynchronous design

In this workload most of the time is spent waiting for the database. In a
synchronous design each waiting request occupies a worker thread and the pool
fills quickly. With async SQLAlchemy and asyncpg, a single event loop keeps
serving other requests while one waits. That is the right model for short,
sudden load.

## Scope

The project focuses only on the concurrency problem. There is no
authentication and no payment step; in a real system stock is first reserved
and released if payment does not complete. Tables are created at startup;
schema changes would need a migration tool such as Alembic.
