---
title: "Rate limits and wildcard DNS in subdomain enumeration"
kisa: A tool that discovers subdomains via DNS, rate-limits itself and filters out wildcard false positives.
ozet: "A tool that finds subdomains like admin., vpn. and test. under a domain using DNS queries. The post focuses on two topics: how rate limiting affects the accuracy of results, and the false positives created by wildcard DNS."
date: 2026-09-18
teknolojiler: [Python, asyncio, dnspython, FastAPI, SQLAlchemy, Docker]
repo: https://github.com/hasancrlk/alt-alan-adi-kesif-araci
kategori: guvenlik
sira: 5
ref: subhound
---

I first came across wildcard DNS records in my Computer Networks course. At
the time it looked like a configuration detail. In this project it turned out
to be something that can make a reconnaissance tool's results meaningless.

## What the tool does

Over time, dozens of subdomains pile up under an organisation's main domain:
`admin.`, `vpn.`, `test.`, `api.`. Some get forgotten, and servers that are no
longer patched stay reachable. Mapping the attack surface starts with finding
these names. In bug bounty programmes and CTFs, it is usually the first step
of reconnaissance as well.

The tool turns 300+ common labels from a built-in list into
`<label>.domain.com` and queries their A, AAAA and CNAME records:

```
$ python -m cli enumerate example.com
Tried        : 315
Found        : 4 live (12 wildcard filtered)
   api.example.com      A       93.184.216.35
*  admin.example.com    A       93.184.216.36
   mail.example.com     CNAME   ghs.googlehosted.com
   www.example.com      A       93.184.216.34
```

## Why rate limiting is about accuracy

`asyncio` runs thousands of queries quickly. There are two separate settings:

- **Concurrency:** how many queries are pending at the same time. Limited
  with `asyncio.Semaphore`, default 50.
- **Rate:** how many queries are sent per second. Limited with a token
  bucket, default 100 per second.

Limiting concurrency alone is not enough. If each of 50 queries takes a few
milliseconds, the per-second count reaches thousands. Most public DNS
resolvers throttle a client at that rate, and they do it not by raising an
error but by returning `SERVFAIL` or `REFUSED`. In the code those answers
look the same as "no record". The scan completes without errors, but the list
is incomplete.

A token bucket allows short bursts while keeping the long-term average,
unlike a fixed sleep between queries. Waiting happens outside the lock, so a
slow task does not stall the whole queue.

```python
self._tokens = min(capacity, self._tokens + elapsed * rate)
```

## Wildcard DNS

If a domain defines a record for `*.example.com`, every non-existent name
gets an answer too. A tool that doesn't notice this reports "found" for every
word in the list.

Before scanning, the tool queries three randomly generated names
(`subhound-<16 hex>.example.com`). If all three answer, the domain is assumed
to have a wildcard and the returned IP set is recorded. Results whose IP set
matches it **exactly** are flagged as wildcard.

Exact matching is used instead of partial matching because a real subdomain
can live on the same server as the wildcard. Filtered results are not deleted;
they are flagged `is_wildcard` and can be shown with `--show-wildcard`.

## Diff report

When a domain is scanned again, subdomains that were not in the previous scan
are marked with `*`. Run regularly, this makes a newly exposed server easy to
spot.

## Scope and limits

Enumeration should only be done on domains you own or are authorised to test.
That is why the tool is rate-limited by default.

In real reconnaissance, Certificate Transparency logs and passive DNS are
more productive than a wordlist; they were not added. A zone transfer
(`AXFR`) attempt was deliberately left out because it sits close to the
authorisation line. There is also no subdomain-takeover check and no punycode
conversion for internationalised domain names.

The project ships with 42 tests; the CLI and the REST API share the same
engine.
