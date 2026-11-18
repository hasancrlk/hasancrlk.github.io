---
title: "Why asyncio and not threading? A concurrent port scanner from scratch"
kisa: A scanner that finds open TCP ports concurrently, guesses the service from its banner and refuses unauthorised targets.
ozet: "I rewrote the most-used slice of nmap, TCP connect scanning and banner grabbing, in my own code. This post is about two decisions: why asyncio, and how the tool protects itself from misuse."
date: 2026-09-18
teknolojiler: [Python, asyncio, FastAPI, SQLAlchemy, argparse, Docker]
repo: https://github.com/hasancrlk/port-tarayici
kategori: guvenlik
sira: 4
ref: portscout
---

## The problem

Every service on a server listens on a port: SSH on 22, the web on 80 and
443, PostgreSQL on 5432. A port left open for no reason is a door. A port
scanner finds those doors. I did not set out to replace `nmap`. I wanted to
write its most common part from scratch and really understand how it works.

```
$ python -m cli scan 127.0.0.1 -p top100
PORT    STATE     SERVICE    PRODUCT / BANNER
--------------------------------------------------------------
22      open      ssh        OpenSSH/SSH: OpenSSH_9.6
```

## Decision 1: Why asyncio?

Port scanning is almost entirely **waiting**. A socket either completes the
handshake or sits idle until the timeout. The CPU does almost nothing.

| | Thread pool | asyncio |
|---|---|---|
| Cost per task | ~1 MB stack | ~1 KB |
| 5,000 ports | Pool stays at 50–200 | 5,000 coroutines, no problem |
| Timeouts | `future.result(timeout=)` does **not** free the thread | `asyncio.wait_for` actually cancels the task |

The last row decided it. In a thread pool, a connection that times out keeps
occupying a slot until the OS closes the socket. On a host that drops packets
(filtered), the whole pool clogs, and that is the most common case while
scanning. `asyncio.wait_for` cancels the coroutine and frees the slot
immediately.

A rough measurement: 1,000 ports on an unresponsive host, 1 s timeout, 200
concurrent connections → about **5 seconds**. Serially it would take about
1,000 seconds.

**Why not unlimited?** Without a `Semaphore`, 65,535 connections start at
once. Locally you get `too many open files`. On the other side it looks like a
SYN flood, so the tool accidentally becomes a denial-of-service attack. The
default is 200 concurrent connections.

## Three states: open, closed, filtered

Simple scanners say "not open means closed". That throws information away:

| State | What happened | Meaning |
|---|---|---|
| open | Handshake completed | Something is listening |
| closed | Got an `RST` | **Host is up**, nothing on that port |
| filtered | No answer at all | Firewall in between, or host down |

If every port comes back `filtered`, the tool does not say "all closed". It
reports that the host was unreachable.

## Banner grabbing

Services like SSH, SMTP and FTP introduce themselves as soon as you connect,
so reading is enough. HTTP waits for a request, so known web ports get a tiny
`HEAD /`. That is the only thing ever sent. The tool never attempts an
exploit.

An easy-to-miss detail: banners are **stripped of control characters** before
printing. Writing a raw banner to the terminal would let a malicious server
send ANSI escape sequences that rewrite your terminal output and log files.

## Decision 2: How does the tool protect itself?

Unauthorised port scanning can be a crime. Instead of writing that in the
README and moving on, I put it in the code: **with the default config, no
internet target can be scanned.**

```
target → resolve to IP
  ├─ name on the allowlist?      ─┐
  ├─ IP local/private?           ─┼─ yes → SCAN
  └─ SCAN_ALLOW_PUBLIC=true?     ─┘
                          no → 403 / exit code 3
```

Three deliberate details:

1. **Both name and IP are checked.** Checking only the name could be bypassed
   with a domain that resolves to an internal IP.
2. **The gate sits in front of the engine.** CLI and API go through the same
   service layer. Calling the API directly with `curl` hits the same check.
3. **Opening it up is a conscious act.** The comment next to the setting in
   `.env` reminds you to get written permission.

## What I deliberately left out

Only TCP connect scanning. SYN scanning needs admin rights, and connect scans
show up in the target's logs as full connections, so they are noisy. No UDP,
no TLS handshake. I **deliberately** did not add IDS-evasion timing profiles
like `nmap -T0`.

## What I learned

I learned the answer to "why asyncio?" from timeout behaviour, not from a
comparison table. The second big lesson: the ethical boundary of an offensive
tool belongs in the code, not in the docs. Users don't read READMEs, but they
do hit gates.
