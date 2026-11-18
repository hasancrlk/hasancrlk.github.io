---
title: "Separating brute-force attacks from forgotten passwords in auth logs"
kisa: An analysis service that finds password-guessing attacks in SSH and web logs and explains every alert.
ozet: "A service that reads SSH and web server login logs and detects brute-force attacks. The focus is on not flagging a user who has simply forgotten their password."
date: 2026-09-18
teknolojiler: [Python, FastAPI, SQLAlchemy, PostgreSQL, pytest, Docker]
repo: https://github.com/hasancrlk/kaba-kuvvet-saldiri-tespiti
kategori: guvenlik
sira: 1
ref: authwatch
---

The `auth.log` of an SSH server exposed to the internet looks roughly like
this:

```
Sep 17 03:12:01 srv01 sshd[4101]: Failed password for invalid user admin from 203.0.113.5
Sep 17 03:12:04 srv01 sshd[4102]: Failed password for invalid user oracle from 203.0.113.5
Sep 17 03:12:07 srv01 sshd[4103]: Failed password for root from 203.0.113.5
Sep 17 03:12:10 srv01 sshd[4104]: Failed password for invalid user postgres from 203.0.113.5
```

The same IP, three seconds apart, a different username each time. This is
clearly a bot probing the door. The same file also contains these lines:

```
Sep 17 09:42:10 srv01 sshd[5210]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:16 srv01 sshd[5211]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:41 srv01 sshd[5212]: Failed password for deniz from 198.51.100.7
```

That is most likely an employee trying to remember a password. Telling the
two apart is a well-known problem in the industry: a system that alerts on
every failed login is soon drowned in noise and its alerts stop being read. I
built this project around that problem as one of the assignments during my
internship at EMT Cyber.

The lines above come from the sample log in the repository; the IP addresses
are from ranges reserved for documentation.

## Counting the threshold correctly

The basic rule is "alert if one IP fails 5 times within 60 seconds". If the
counter is reset every minute, an attacker can stay under the threshold by
making 4 attempts at the end of one window and 4 at the start of the next.
Counting is therefore done with a **sliding window**: a `deque` per IP, and
when a new failure arrives, entries that have fallen out of the window are
dropped.

```python
bucket.append(event)
while bucket and event.timestamp - bucket[0].timestamp > window:
    bucket.popleft()
if len(bucket) >= threshold:
    raise_alert()
```

Each entry enters and leaves the queue once, so the cost is linear and a
large log is processed in a single pass. The 4+4 sequence that a fixed window
misses is a separate test in the repository.

A cooldown prevents an alert for every attempt after the threshold is
crossed. The default is 300 seconds, during which no new alert is written for
the same IP.

## Telling a user from a bot

Not every burst over the threshold is an attack. The service computes a
confidence score for each alert based on the shape of the attempts:

- **Username variety.** Three or more distinct usernames raise the score; a
  single username lowers it.
- **Non-existent users.** `invalid user` lines indicate user enumeration and
  raise the score.
- **Regularity of intervals.** The coefficient of variation of the gaps is
  computed. People retry at irregular intervals; automation is regular.
- **Intensity.** Three times the threshold or more raises the score.
- **History.** A previous successful login from the same IP lowers it.

The result is labelled `high`, `medium` or `low`, and each alert carries the
reasons behind it as sentences. For the two examples above (the tool writes
its reasons in Turkish; translated here):

```
203.0.113.5   confidence: high (0.95)
  - 5 distinct usernames tried (user enumeration).
  - 4 attempts targeted non-existent usernames.
  - Attempts arrived at near-constant intervals (automation).

198.51.100.7  confidence: low (0.0)
  - Single username - possibly a user who forgot the password.
  - This IP has logged in successfully before (known source).
```

Low-confidence alerts are not deleted, only labelled. The analyst decides
what can be ignored; the service only makes triage easier.

In web access logs the username is usually `-`. In that case the
"single username" discount is not applied; otherwise the score of a real bot
burst would be lowered unfairly.

## Success after failures

If one IP fails repeatedly against the same username and then logs in
successfully as that user, the service raises a separate alert:
`possible_account_takeover`. The username has to match. A normal login as
`deploy` after an attack on `admin` does not qualify.

## Supported logs

SSH `auth.log`, nginx/apache combined logs and JSON lines. Lines that match
no format are counted and samples are kept, so every upload shows how much
of the file could not be read. Because `auth.log` timestamps carry no year,
the year is passed as a parameter on upload.

## Out of scope

- **Distributed attacks.** Detection is per IP. A botnet making a few
  attempts from each IP never reaches the threshold; that needs a per-user or
  per-network (ASN) dimension.
- **State across uploads.** Each upload is processed on its own, so an attack
  split across two files can be cut in half.
- **Reverse proxies.** `X-Forwarded-For` is not read.
- **Authentication.** The service itself is open and should run on an
  internal network or behind a reverse proxy.

The project ships with 48 tests and starts with PostgreSQL via
`docker compose up`. Since the sample log is in the repository, it can be
tried right after installation.
