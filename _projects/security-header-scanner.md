---
title: "The header is there but doesn't protect: grading web security headers A to F"
kisa: A scanner that scores web security headers by their values, not just their presence, and suggests ready-to-paste fixes.
ozet: "I built a scanner that checks a website's security headers and gives it an A–F grade. It doesn't ask whether a header exists. It asks whether it actually protects."
date: 2026-09-18
teknolojiler: [Python, httpx, FastAPI, SQLAlchemy, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/http-guvenlik-basligi-tarayici
kategori: guvenlik
sira: 6
ref: headerguard
---

## The problem

With every page, a website sends invisible security headers to the browser:
"only open this site over HTTPS" (HSTS), "only load scripts from these
sources" (CSP), "don't embed my page in another site" (X-Frame-Options). When
they are missing or wrong the site keeps working. The problem only shows up
during an attack.

Many existing checkers only ask "is the header present?", which gives a good
grade to this:

```
Strict-Transport-Security: max-age=1
```

The header **exists**. And it protects for exactly one second, which means it
doesn't.

## Hard part 1: Ratios instead of present/absent

Each header has sub-checks, and every failed check lowers that header's score
ratio:

| Header | Value | Ratio | Why |
|---|---|---|---|
| HSTS | `max-age=31536000; includeSubDomains` | 1.00 | Complete |
| HSTS | `max-age=31536000` | 0.80 | Subdomains unprotected |
| HSTS | `max-age=60` | 0.50 | Shorter than 6 months |
| CSP | `default-src 'self'; script-src 'unsafe-inline'` | 0.60 | Hole in XSS protection |

The total is a weighted average. CSP (22) and HSTS (18) weigh the most.
Headers like a version-leaking `Server: nginx/1.24.0`, `X-Powered-By` and
`Access-Control-Allow-Origin: *` cost penalty points.

Two special cases got extra thought:

- **A plain-HTTP site isn't additionally penalised for missing HSTS.** The
  real problem is HTTP itself, which is a separate high-severity finding.
  Counting the same gap twice would push the grade down artificially.
- **No `X-Frame-Options` but CSP has `frame-ancestors` → full marks.**
  Punishing the modern, correct configuration for not carrying the legacy
  header would be wrong.

## Hard part 2: Rules live in a file, not in code

Rules live in `data/rules.json`. An organisation can write its own policy
without touching the code:

```json
{
  "name": "strict-transport-security",
  "weight": 18,
  "advice": "Strict-Transport-Security: max-age=31536000; includeSubDomains",
  "checks": [
    { "type": "directive_min", "directive": "max-age", "min": 15768000, "penalty": 0.5 },
    { "type": "must_contain", "value": "includesubdomains", "penalty": 0.2 }
  ]
}
```

That raises a security question: a flexible rules file must not give whoever
can edit it a way to **run code**. So check types come from a fixed set. An
unknown type makes the file fail to load instead of being skipped silently.
Regular expressions are compiled at startup and there is no `eval` path.

The active rules are readable at `GET /rules`. A grade you can't see the
formula for can't be argued with either. "Why did we get a C?" deserves an
answer.

## Hard part 3: Redirects

I don't let `httpx` follow redirects automatically; I follow them by hand.
Automatic following only shows the last response's headers, but the chain
itself is a finding:

```
http://site.com → https://site.com → https://www.site.com
                                      ↑ HSTS is here, but the first request was plain HTTP
```

A chain that starts at `https://` and ends at `http://` is reported as a
high-severity **protocol downgrade**. An unreachable target doesn't crash the
scan. Each target is evaluated on its own and shows up with its error type.

## Cookies, TLS and the diff report

Cookies are checked for `Secure`, `HttpOnly` and `SameSite`. The TLS
certificate's subject, issuer and days until expiry are reported. There is
also a report comparing two scans. I closed a trap there: only targets present
in both scans are compared, so removing a bad site from the list doesn't look
like an "improvement" just because the average went up.

## What I deliberately left out

Only the site's root page is scanned. JavaScript isn't executed, so CSP set
via `<meta>` isn't seen. CSP analysis is shallow: `unsafe-inline` is caught,
but nonce/hash strategies aren't evaluated. Most importantly: **an A doesn't
mean the site is secure.** Headers are just one layer of defence.

## What I learned

Designing a scoring system is as much about fairness as it is technical. Every
rule should pass the question "could this wrongly punish or reward a
configuration?". I also learned that configurability opens an attack surface.
Flexibility has to be bounded so it can never turn into code execution.
