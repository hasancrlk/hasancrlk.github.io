---
title: "50 consoles, 300 buyers: why stock goes negative in a flash sale, and how to stop it"
kisa: A backend service that proves, with a test, that stock never goes negative under hundreds of concurrent purchases.
ozet: "What happens when 300 people try to buy at the same time and only 50 items are in stock? I answered that with a single SQL statement and proved it with a test."
date: 2026-08-31
teknolojiler: [Python, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, pytest]
repo: https://github.com/hasancrlk/Es_Zamanlilik_Stok_Yonetimi
kategori: backend
sira: 7
ref: stok
---

## The problem

An online shop runs a flash sale. There are 50 game consoles in stock and the
moment the campaign starts, hundreds of people hit "Buy". Two things must not
happen:

1. **Overselling.** Selling items you don't have.
2. **Lock-up.** The site stops responding under load.

This small service lists products and handles purchases. Its real purpose is
to show how to solve the first point correctly.

## The wrong way: read, then write

The first code that comes to mind:

```python
item = await db.get(Item, item_id)     # 1. read the stock
if item.stock >= qty:                   # 2. enough?
    item.stock -= qty                   # 3. decrement and save
```

With one user it works perfectly. When two requests run step 1 at the same
time, both see "1 left" and both complete the sale. This is a **lost update**.
Result: stock is `-1`.

What makes this bug sneaky is that it almost never shows up during
development. Clicking through it locally one request at a time, it never
happens. It only appears under real load.

## The right way: one atomic statement

Instead of separating the check from the decrement, I merged them into one SQL
statement:

```python
result = await db.execute(
    update(Item)
    .where(Item.id == item_id, Item.stock >= body.quantity)
    .values(stock=Item.stock - body.quantity)
    .returning(Item.stock)
)
new_stock = result.scalar_one_or_none()
```

Why is this safe?

1. PostgreSQL takes a **row lock** automatically while updating the row.
2. Other requests for the same row **wait in line** until the first
   transaction finishes.
3. When its turn comes, each request re-evaluates `stock >= qty` **against
   the current value**. If there isn't enough stock, no row is updated.
4. If no row was updated, the service checks whether the product exists and
   returns `404` or `409` accordingly.

No extra `SELECT ... FOR UPDATE`, application-level lock or retry loop needed.

### The last safety net

The table has a database constraint: `CHECK (stock >= 0)`. Even if the code is
changed by mistake one day, the database rejects negative stock. Keeping the
rule in the database means the protection survives when a code path is
forgotten.

## The proof

Saying a rule "works" isn't enough; a test has to show it:

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
    # and the final stock in the database is exactly 0
```

Exactly 50 of the 300 requests succeed, 250 get "out of stock", and the final
stock stays at 0. The test runs against a real PostgreSQL, because row-lock
behaviour can't be tested with SQLite.

## Why async?

In this workload most of the time is spent waiting for the database. In
synchronous code each waiting request ties up a worker thread and the pool
fills quickly. With async SQLAlchemy and asyncpg, a single event loop keeps
serving other requests while one waits for the database. That is the right
model for short, sudden spikes.

## What I deliberately left out

No authentication and no payment step. In real life stock is reserved first
and released if payment doesn't complete. Tables are created on startup;
schema changes would need a migration tool (Alembic).

## What I learned

I learned to solve concurrency bugs not by "writing careful code" but by
**handing the job to the database**. Its row locking is more reliable than any
lock I could write. Second lesson: a guarantee like this can only be proven by
a test that sends concurrent requests. A test that sends them one by one
always passes.
