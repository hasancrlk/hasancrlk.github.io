---
title: "Scoring security headers by their values"
kisa: A scanner that scores web security headers by their values, not just their presence, and suggests ready-to-paste fixes.
ozet: "A scanner that inspects a website's HTTP security headers and gives it a 0–100 score and an A–F grade. It checks not only whether a header exists but whether its value actually provides protection."
date: 2026-09-18
teknolojiler: [Python, httpx, FastAPI, SQLAlchemy, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/http-guvenlik-basligi-tarayici
kategori: guvenlik
sira: 6
ref: headerguard
---

The following line is a valid HTTP response header:

```
Strict-Transport-Security: max-age=1
```

Because the header is present, a check that only looks at presence treats the
site as compliant. But `max-age=1` tells the browser to remember the rule for
one second. HeaderGuard was written to tell such cases apart.

## Scoring

Each header has a weight and a set of sub-checks. Every failed check lowers
the header's score ratio. The total is the weighted average of the ratios,
minus penalty points.

The highest weights follow each header's role in protection:

- **Content-Security-Policy (22):** the strongest header for limiting XSS.
- **Strict-Transport-Security (18):** blocks HTTPS-to-HTTP downgrade attacks.
- **X-Frame-Options (10):** prevents the page from being framed by another
  site, i.e. clickjacking.
- **X-Content-Type-Options and Referrer-Policy (8 each):** MIME sniffing and
  address leakage.

Some examples:

- `max-age=31536000; includeSubDomains` → HSTS gets full marks.
- `max-age=31536000` → ratio 0.80, subdomains stay unprotected.
- `max-age=60` → ratio 0.50, shorter than six months.
- A CSP containing `script-src 'unsafe-inline'` → ratio 0.60.

Headers such as a version-revealing `Server: nginx/1.24.0`, `X-Powered-By`
and `Access-Control-Allow-Origin: *` cost penalty points.

Two cases are handled specially. On a site served over plain HTTP, a missing
HSTS header is not penalised separately; the real issue is the use of HTTP
itself, reported as its own high-severity finding. If the CSP defines
`frame-ancestors`, a missing `X-Frame-Options` costs nothing, because that is
the modern configuration.

## Rules live in a file, not in code

Scoring rules are kept in `data/rules.json`. An organisation can define its
own policy without changing the code:

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

A configurable file must not give whoever can edit it a way to run code.
Check types therefore come from a fixed set, and an unknown type stops the
file from loading. Regular expressions are compiled at startup, and there is
no `eval` path. The active rules can be read from `GET /rules`, so the way a
grade was calculated is always visible.

## Redirects

Redirects are followed by hand rather than left to `httpx`. With automatic
following, only the last response's headers are visible, while the chain
itself can be a finding. A chain that starts at `https://` and ends at
`http://` is reported as a high-severity **protocol downgrade**. More than 10
redirects are treated as a loop.

An unreachable target does not stop the whole scan; each target is evaluated
separately and appears in the result with its error type.

## Cookies, TLS and comparison

Cookies are checked for `Secure`, `HttpOnly` and `SameSite`. The TLS
certificate's subject, issuer and days until expiry are reported. When two
scans are compared, only targets present in both are considered, so removing
a target from the list cannot raise the average and look like an
improvement.

## Limits

Only the site's root page is scanned and JavaScript is not executed, so a CSP
set via a `<meta>` tag is not seen. CSP analysis catches obvious weaknesses
such as `unsafe-inline` and `default-src *` but does not evaluate nonce and
hash strategies. A high grade does not mean the site is secure; headers are
only one layer of defence.

The project ships with 53 tests.
