---
title: "Speed or politeness? The silent-incomplete-results trap in subdomain enumeration"
kisa: A tool that discovers subdomains via DNS, rate-limits itself and filters out wildcard false positives.
ozet: "I built a tool that finds subdomains like admin., vpn. and test. under a domain. The most interesting problem came from an unexpected place: when the tool is too fast, it does not fail. It silently returns fewer results."
date: 2026-09-18
teknolojiler: [Python, asyncio, dnspython, FastAPI, SQLAlchemy, Docker]
repo: https://github.com/hasancrlk/alt-alan-adi-kesif-araci
kategori: guvenlik
sira: 5
ref: subhound
---

## The problem

An organisation doesn't just have `company.com`. Over time dozens of
subdomains pile up, like `admin.company.com`, `vpn.company.com` and
`test.company.com`, and some get forgotten. An unpatched test server stays
online. The attacker's reconnaissance starts by finding exactly these names.
Defenders should build the same list themselves.

The method is simple: turn 300+ common labels (`admin`, `api`, `mail`…) into
`<label>.company.com` and ask DNS.

```
$ python -m cli enumerate example.com
Tried        : 315
Found        : 4 live (12 wildcard filtered)
   api.example.com      A       93.184.216.35
*  admin.example.com    A       93.184.216.36
   mail.example.com     CNAME   ghs.googlehosted.com
```

## Hard part: Two separate knobs

You need to run thousands of DNS queries fast without overwhelming the
resolver. The key insight was that these are **two different** questions:

| Question | Tool | Default |
|---|---|---|
| How many queries in flight at once? | `asyncio.Semaphore` | 50 |
| How many queries per second? | Token bucket | 100/s |

Limiting concurrency alone is not enough. If each of 50 concurrent queries
takes 5 ms, that is 10,000 queries per second. Most public resolvers throttle
you at that rate, and **the throttling is silent**. Queries that return
`SERVFAIL` or `REFUSED` look like "not found" in the code. The scan finishes,
the list is short, and nobody realises anything went wrong. A tool that
crashes is far less dangerous than one that quietly returns incomplete
results.

### Why a token bucket?

Sleeping a fixed `1/rate` between queries is simple but rigid. A token bucket
allows short bursts while keeping the long-term average, which suits DNS,
because resolvers typically look at the per-second average.

```python
self._tokens = min(capacity, self._tokens + elapsed * rate)
```

The waiting happens **outside** the lock. Holding the lock while waiting would
let one slow task stall the entire queue.

## Wildcard DNS: 300 fake "found"s

Some domains define a record for `*.company.com`. On such a domain **every**
query gets an answer. A tool that doesn't notice produces 300 "found" entries
from a 300-line list, all garbage.

```
1. Ask for 3 random names:    subhound-<16 hex>.company.com
2. All of them answer         → wildcard present, record the IP set
3. Any of them is empty       → no wildcard
4. Flag findings whose IP set matches exactly
```

Two deliberate decisions:

- **Why an exact match?** A real subdomain can live on the same server as the
  wildcard, for example behind the same reverse proxy. Partial matching would
  throw away real findings.
- **Why flag instead of delete?** Filtered records are kept and stamped
  `is_wildcard`. `--show-wildcard` reveals them. "I found this but filtered
  it, have a look if you want" beats throwing it away silently.

## Diff report

When a domain is rescanned, subdomains that were not in the previous scan are
marked with `*`. A team running this regularly sees a forgotten new server on
day one.

## What I deliberately left out

In real reconnaissance, Certificate Transparency logs and passive DNS are
more productive than a wordlist. I did not add them. Some tools try a zone
transfer (`AXFR`); I **deliberately** left it out because it sits close to the
authorisation line. There is no subdomain-takeover check either.

## What I learned

The most valuable lesson: the most dangerous failure mode of a tool is silent
incompleteness. A crashing program gets noticed. A program that returns a
partial list inspires confidence and misleads. The rate limit looked like a
"politeness" feature. It turned out to be a correctness feature.
