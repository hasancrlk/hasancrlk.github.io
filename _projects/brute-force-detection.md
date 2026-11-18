---
title: "Forgetful user or bot? Detecting brute-force attacks from auth logs"
kisa: An analysis service that finds password-guessing attacks in SSH and web logs and explains every alert.
ozet: "I built a service that reads server logs and detects brute-force attacks. Finding the attack was the easy part. The real work was not flagging the employee who forgot their password."
date: 2026-09-18
teknolojiler: [Python, FastAPI, SQLAlchemy, PostgreSQL, pytest, Docker]
repo: https://github.com/hasancrlk/kaba-kuvvet-saldiri-tespiti
kategori: guvenlik
sira: 1
ref: authwatch
---

## The problem

Every login attempt on a server becomes a line in a log file. Open the
`auth.log` of any SSH server exposed to the internet and you will see lines
like `Failed password for invalid user admin` several times a minute. Bots are
knocking on the door all the time.

The rule sounds simple: "alert when one IP fails 5 times within 60 seconds."
It takes five minutes to write, and it fails in two ways:

1. An attacker can sidestep it easily.
2. An employee who mistypes their password three or four times also triggers
   it. After a while nobody looks at the alerts.

This project tries to solve both.

## Hard part 1: A fixed window can be gamed

If you reset a counter every 60 seconds and the threshold is 5, the attacker
sends 4 attempts at the end of one window and 4 more right after the reset.

```
window 1                           window 2
├───────────────────────────┤      ├──────────────────────
     ✗  ✗  ✗  ✗  (4 tries)          ✗  ✗  ✗  ✗  (4 tries)
                         ↑ 55 s     ↑ 62 s

fixed window  : 4 tries in each window → NO ALERT
sliding window: at 62 s, look back 60 s → 8 tries → ALERT
```

The fix is a **sliding window**. I keep a `deque` per IP and drop events that
fall out of the window whenever a new failure arrives:

```python
bucket.append(event)
while bucket and event.timestamp - bucket[0].timestamp > window:
    bucket.popleft()          # drop events outside the window
if len(bucket) >= threshold:
    raise_alert()
```

Each event enters and leaves the queue once, so the cost is linear. A
million-line log is processed in a single pass. The attack sequence above is a
test in the repository.

I also added a **cooldown**. Without it, a 500-attempt attack would produce
496 alerts. The same IP is silenced for 5 minutes after an alert.

## Hard part 2: Telling humans from bots

Not every burst over the threshold is an attack. The difference is in the
**shape** of the attempts:

| Signal | Human | Bot | Score effect |
|---|---|---|---:|
| Distinct usernames tried | 1 | many | 3+ → +0.25, single → −0.15 |
| Non-existent user (`invalid user`) | no | often | +0.20 |
| Regularity of the gaps | irregular | clockwork | regular → +0.15 |
| Multiple of the threshold | low | high | 3× → +0.25 |
| Earlier successful login from this IP | usually | rarely | −0.20 |

Regularity comes from the **coefficient of variation** of the gaps between
attempts. A person waits 3 seconds, then 12, then 40. A bot ticks like a
clock. The total is labelled `high / medium / low`, and every alert explains
itself in plain sentences. Two real outputs from the sample log in the repo
(the tool writes its reasons in Turkish; translated here):

```
203.0.113.5  →  5 usernames, 4 of them non-existent, exactly 3 s apart
                confidence: high (0.95)
                "5 distinct usernames tried (user enumeration)."
                "Attempts came at near-constant intervals (automation)."

198.51.100.7 →  one account, irregular gaps, same IP logged in this morning
                confidence: low (0.0)
                "Single username - possibly a user who forgot the password."
```

Two design decisions. First, **low-confidence alerts are not deleted**, only
labelled. A system that filters itself can silently swallow a real attack; the
analyst makes the call. Second, web logs usually carry `-` instead of a
username. Treating that as "single user" and lowering the score would unfairly
downgrade a real bot burst. No signal, no discount.

## Account takeover

If one IP fails repeatedly against **the same username** and then logs in
successfully as that user, that is a separate alert type:

```
22:05:00  ✗ hasan    ┐
  ...                ├─ 6 failures
22:05:45  ✗ hasan    ┘
22:05:54  ✓ hasan    ← possible account takeover (confidence: high)
```

The username must match. Six attacks on `admin` followed by a normal login as
`deploy` is not a takeover. Matching it would flag every developer who logs in
in the morning.

## Log parsing

Three formats are supported: SSH `auth.log`, nginx/apache combined logs and
JSON lines. Unparseable lines are not thrown away; they are counted and
samples are stored. Saying "1 of 30 lines could not be read, here it is" beats
dropping it silently. A small trap: `auth.log` does not write the year
(`Sep 17 03:12:01`), so the year is passed as a parameter on upload.

## What I deliberately left out

- **Distributed attacks are invisible.** Detection is per IP. A botnet making
  2 attempts from each IP never crosses the threshold. That needs a per-user
  or per-network (ASN) dimension.
- **No state between uploads.** An attack split across two files can be cut
  in half. Real-time streaming would need persistent state.
- **No proxy awareness.** `X-Forwarded-For` is not read.

## What I learned

The value of a detection system is not how many attacks it catches but how
many of its **alerts are trusted**. Nobody keeps reading a bare "ALERT" line.
People read the alert that answers "why". The project ships with 48 tests. My
favourite one shows the sliding window catching the sequence the fixed window
misses.
