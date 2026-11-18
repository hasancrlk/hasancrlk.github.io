---
title: "When the attacker tries to erase their tracks: signed file integrity monitoring"
kisa: A forensics tool that takes a signed fingerprint of a folder and finds files that were later changed, added or deleted.
ozet: "I built a tool that fingerprints a folder and later finds which files changed. The real question was: what happens if the attacker changes the fingerprint itself?"
date: 2026-09-17
teknolojiler: [Python, FastAPI, SQLAlchemy, Alembic, Typer, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/dosya-butunlugu-izleme
kategori: guvenlik
sira: 2
ref: fim-sentinel
---

## The problem

An attacker who breaks into a web server usually leaves traces. They inject a
script into the home page, drop a backdoor called `shell.php` or edit a config
file. These changes can go unnoticed for weeks.

**File Integrity Monitoring** (FIM) is an old and effective defence. First you
take a fingerprint of the folder in its clean state, called a baseline. Then
you rescan it regularly and compare:

```
$ python -m cli.fim_cli scan --baseline-id 1
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Type     ┃ File Path                ┃ Detail                  ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ MODIFIED │ /var/www/html/index.html │ Hash mismatch detected. │
│ MODIFIED │ /var/www/html/config.php │ Hash mismatch detected. │
│ ADDED    │ /var/www/html/shell.php  │ New file detected.      │
└──────────┴──────────────────────────┴─────────────────────────┘
```

That part is easy. The hard question is: **what if the attacker edits the
baseline too?** Someone with database access adds `shell.php` to the baseline
and the tool reports that everything is fine.

## Hard part: Chain of custody

In digital forensics this is called **chain of custody**: being able to prove
that evidence was not tampered with. I built five layers for it.

**1. Baselines are signed.** Every baseline is signed with a secret key
(HMAC-SHA256). The signature is computed over a canonical form that does not
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

A baseline edited in the database is rejected at scan time (HTTP 409), and the
attempt itself is recorded.

**2. The audit log is chained.** Every operation is written to an audit log
and each row is bound to the hash of the previous one. Deleting a row, editing
one or reordering them breaks the chain. The `verify-audit` command checks the
chain end to end and points at the broken row. On PostgreSQL a trigger also
blocks UPDATE and DELETE.

**3. Permissions are tracked, not just content.** Next to the SHA-256 hash,
size, file mode and owner are stored. A file whose content stays the same but
becomes world-writable is a finding too.

**4. Symlinks are not followed.** The link target is recorded instead. Re-pointing
a link is detected and nothing outside the monitored folder is ever read:

```python
if stat.S_ISLNK(st.st_mode) and not follow_symlinks:
    target = os.readlink(file_path)
    result.sha256 = hashlib.sha256(f"symlink:{target}".encode()).hexdigest()
```

**5. Unreadable is not "deleted".** A file that exists but cannot be read
because of permissions is reported as an error. Reporting it as `DELETED`
would send the investigator after the wrong story.

> Where the key lives matters. Anyone holding both the database and
> `FIM_HMAC_KEY` can forge a baseline. The key belongs outside the monitored
> host, in a secrets manager.

## Large files

Files are read and hashed in 64 KB chunks, so a multi-gigabyte file does not
blow up memory. Permission errors and symlink loops are logged; the tool does
not crash.

## Wiring it into automation

The `scan` command exits with code **2** when it finds changes. That small
detail makes it easy to hook into cron or CI:

```bash
0 * * * * fim-sentinel scan -b 1 || echo "Integrity alert" | mail -s FIM admin@example.com
```

## What I learned

When designing a security tool, ask: "what would the attacker do to this tool
itself?" Writing a tool that detects changes is easy. Writing one that can
prove its own records were not changed is the real work. That question led me
to signatures, a chained log and a database trigger. The CLI and the REST API
share the same service layer, so no rule has to be written twice.
