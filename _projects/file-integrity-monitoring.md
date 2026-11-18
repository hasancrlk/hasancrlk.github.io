---
title: "A tool I hadn't heard of before my internship: file integrity monitoring"
kisa: A forensics tool that takes a signed fingerprint of a folder and finds files that were later changed, added or deleted.
ozet: "I first came across file integrity monitoring (FIM) during my internship. This post covers the tool that finds changed files, and how it protects its own records against tampering."
date: 2026-09-17
teknolojiler: [Python, FastAPI, SQLAlchemy, Alembic, Typer, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/dosya-butunlugu-izleme
kategori: guvenlik
sira: 2
ref: fim-sentinel
---

When I started my internship at EMT Cyber, I had not heard the term "File
Integrity Monitoring". When it was given to me as an assignment, the first
step was understanding what it is and why it is so widely used.

## The concept

An attacker who breaks into a server often leaves traces in the file system:
injected code in a page, an uploaded backdoor, a modified config file. File
integrity monitoring catches these changes in two steps:

1. Take a fingerprint of the folder in a trusted state, called a
   **baseline**.
2. Rescan the folder periodically and compare it with the baseline.

On the command line:

```
$ python -m cli.fim_cli baseline --path /var/www/html
$ python -m cli.fim_cli scan --baseline-id 1

│ MODIFIED │ /var/www/html/index.html │ Hash mismatch detected. │
│ MODIFIED │ /var/www/html/config.php │ Hash mismatch detected. │
│ ADDED    │ /var/www/html/shell.php  │ New file detected.      │
```

For every file the SHA-256 hash, size, permissions and ownership are stored.
Files are read in 64 KB chunks, so large files don't strain memory.

## The real question: the records themselves

However accurate the comparison is, the baseline lives in a database. An
attacker with database access can add the `shell.php` they uploaded to the
baseline as well, and the scan will then show no change.

In digital forensics this is addressed by **chain of custody**: being able to
prove that evidence has not changed since it was collected. The tool has the
following safeguards:

**Baselines are signed.** Each baseline is signed with HMAC-SHA256 using
`FIM_HMAC_KEY`. The signature is computed over sorted rows, so it does not
depend on file order:

```python
def sign_baseline(target_path, follow_symlinks, entries) -> str:
    mac = hmac.new(get_hmac_key(), digestmod=hashlib.sha256)
    mac.update(json.dumps([target_path, bool(follow_symlinks)]).encode() + b"\n")
    rows = sorted(
        [_get(e, k) for k in ("file_path", "sha256", "size_bytes", "mode", "uid", "gid")]
        for e in entries
    )
    for row in rows:
        mac.update(json.dumps(row, separators=(",", ":")).encode() + b"\n")
    return mac.hexdigest()
```

A scan against a baseline whose signature doesn't match is rejected with
HTTP 409, and the attempt is written to the audit log.

**The audit log is chained.** Every operation is written to an audit log and
each row is bound to the hash of the previous row. Deleting, editing or
reordering a row breaks the chain; the `verify-audit` command shows where.
On PostgreSQL a trigger also blocks UPDATE and DELETE on that table.

**Symlinks are not followed.** The link target is recorded instead, so
re-pointing a link shows up as a change and files outside the monitored
folder are never read.

**Unreadable is not deleted.** A file that cannot be read because of
permissions is reported as an error, not as `DELETED`. In a forensic
investigation this distinction prevents a wrong conclusion.

`FIM_HMAC_KEY` must be stored separately from the monitored server's
database. An attacker with access to both the database and the key could
re-sign the baseline; this is a documented limit of the tool.

## Everyday use

The `scan` command exits with code 2 when it finds changes, so the tool can
be wired directly into scheduled jobs:

```bash
0 * * * * fim-sentinel scan -b 1 || echo "Integrity alert" | mail -s FIM admin@example.com
```

The same operations are available over a REST API. The API requires an
`X-API-Key` header and can only scan folders allowed in `FIM_ALLOWED_PATHS`.
The CLI and the API share one service layer, so no rule is written twice.
