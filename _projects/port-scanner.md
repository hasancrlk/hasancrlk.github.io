---
title: "I used nmap, then I wrote my own port scanner"
kisa: A scanner that finds open TCP ports concurrently, guesses the service from its banner and refuses unauthorised targets.
ozet: "I had worked with nmap before. In this project I wrote its most-used part, TCP connect scanning and banner grabbing, from scratch with asyncio, and added a scope gate to prevent misuse."
date: 2026-09-18
teknolojiler: [Python, asyncio, FastAPI, SQLAlchemy, argparse, Docker]
repo: https://github.com/hasancrlk/port-tarayici
kategori: guvenlik
sira: 4
ref: portscout
---

Before this project I knew port scanning as an nmap user: type the command,
read the output. Doing the same job in my own code showed me which network
behaviour sits behind every word in that output.

PortScout was not written to replace nmap but to understand its most commonly
used part: TCP connect scanning and reading the first line a service sends
to introduce itself (the banner).

```
$ python -m cli scan 127.0.0.1 -p top100
PORT    STATE     SERVICE    PRODUCT / BANNER
22      open      ssh        OpenSSH/SSH: OpenSSH_9.6
```

## The concurrency model

Port scanning is mostly waiting. Each connection either completes the
handshake or waits for a reply until the timeout; the CPU does almost nothing
in the meantime. `asyncio` was chosen for this workload.

The deciding factor was how timeouts are handled. In a thread pool,
`future.result(timeout=...)` stops waiting but does not free the thread; it
keeps occupying a slot until the OS closes the connection. On an
unresponsive host this fills the pool quickly. `asyncio.wait_for` cancels the
coroutine and the slot is freed immediately.

Concurrency is not unlimited. Without an `asyncio.Semaphore`, thousands of
connections would try to open at once: locally they hit the file descriptor
limit, and on the other side they resemble a SYN flood. The default is 200
concurrent connections, adjustable with `--concurrency`.

As a rough measurement: 1,000 ports on an unresponsive host, a 1-second
timeout and 200 concurrent connections complete in about 5 seconds.

## Three port states

The scanner reports one of three states for each port:

- **open:** the TCP handshake completed; something is listening.
- **closed:** the other side sent `RST`. The host is up but nothing listens
  on this port.
- **filtered:** no answer at all. There may be a firewall in between, or the
  host may be down.

The difference between `closed` and `filtered` matters during
reconnaissance. If every port comes back `filtered`, the tool adds a note
that the host could not be reached instead of saying "all closed".

## Banner grabbing

Services like SSH, SMTP and FTP send a greeting line as soon as a connection
is made; reading it is enough. HTTP waits for a request, so known web ports
receive only a `HEAD /`. The text is mapped to a product (OpenSSH, Postfix,
nginx, Redis and so on) with a lookup table. The tool never attempts any
exploit.

Banner text is stripped of control characters before it is printed. If raw
text went straight to the terminal, a server sending ANSI escape sequences
could alter the terminal output and log files.

## The scope gate

Unauthorised port scanning can be a criminal offence. So the rule was not
left as a warning in the README; it was put into the code: **with the default
configuration, no target on the internet can be scanned.**

A target can be scanned only if one of these holds:

1. Its name is on the allowlist (`SCAN_ALLOWLIST`).
2. It resolves to a local or private IP address.
3. `SCAN_ALLOW_PUBLIC=true` has been set deliberately.

Both the name and the resolved IP are checked. The gate sits in front of the
scan engine; the CLI and the REST API go through the same service layer, so
someone calling the API directly faces the same check. An out-of-scope
target is rejected with exit code 3 on the CLI and 403 on the API.

## Deliberately not included

- **SYN scanning:** needs raw sockets and admin rights.
- **UDP scanning:** meaningful results need service-specific packets.
- **TLS handshake:** 443 shows as open but certificate data isn't read.
- **Timing profiles:** detection-evasion profiles like nmap's `-T0` were not
  added.

The project ships with 38 tests. Results are saved to SQLite or PostgreSQL
and previous scans can be listed with `python -m cli list`.
