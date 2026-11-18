---
title: "Encrypting files without storing the password"
kisa: An API service that encrypts files with a password and supports one-time and time-limited downloads.
ozet: "An API service that encrypts files with a password and offers one-time and expiring download links. This post covers the algorithms and parameters chosen, and what the service does not promise."
date: 2026-09-17
teknolojiler: [Python, FastAPI, cryptography, Argon2id, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/sifreli-dosya-kasasi
kategori: guvenlik
sira: 3
ref: vaultcore
---

The most common way to share a sensitive file is to attach it to an email,
and the biggest drawback is that it then sits unencrypted on a server for
years. This service was written to meet three requirements together:

- Files are written to disk only in encrypted form.
- The password is never stored anywhere.
- A file becomes inaccessible after a set number of downloads or a set time.

```bash
curl -X POST http://localhost:8000/api/v1/vault/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@contract.pdf" -F "password=long-and-strong-passphrase" \
  -F "max_downloads=1" -F "expires_in_hours=24"
```

## The encryption flow

The password is first turned into a 256-bit key with Argon2id. That key
encrypts the file with AES-256-GCM. Each file gets its own salt (16 bytes)
and nonce (12 bytes). The database stores the salt, the nonce and file
metadata; it never stores the password or the key.

```python
def encrypt(plaintext: bytes, password: str, aad: bytes | None = None):
    params = _get_crypto_params()
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt, params)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptionResult(ciphertext=ciphertext, salt=salt, nonce=nonce, params=params)
```

### Why AES-GCM?

AES-GCM is an AEAD mode that provides confidentiality and integrity in one
operation. With AES-CBC a MAC would have to be added separately and applied
in the right order, a step that is prone to implementation errors. GCM uses
no padding, so it is not affected by padding-oracle attacks, and it is
hardware-accelerated on modern CPUs.

The one point that needs care is never reusing a nonce with the same key.
The service generates a fresh nonce with `os.urandom` for every encryption.

### Why Argon2id?

User passwords have low entropy. Used directly as a key, a password allows an
attacker to try a very large number of guesses very quickly. Argon2id uses a
large amount of memory for every derivation (64 MB, 3 passes, 4 threads in
this project). Because memory is limited on GPUs, the cost of parallel
guessing rises considerably.

Argon2 parameters are stored with each file, so strengthening them later
does not break older files.

## Implementation details

- **The file ID is bound to the ciphertext.** It goes into AES-GCM's
  associated data (AAD). If the ciphertexts of two files are swapped in the
  database, authentication fails.
- **Errors are indistinguishable.** A wrong password and corrupted data
  produce the same response, so no extra information leaks.
- **Two layers of rate limiting.** 5 download attempts per minute per IP,
  and a file is locked for 15 minutes after 5 wrong passwords. The second
  layer also works against attempts from many IPs.
- **Atomic download counter.** Of two simultaneous requests to a one-time
  link, only one succeeds.
- **Bounded resource use.** Uploads are read in chunks and the number of
  concurrent key derivations is capped.
- **Cleanup.** Encrypted data of expired, exhausted or deleted files is also
  removed from disk.

## What the service does not promise

For a while the repository's GitHub description said "zero-knowledge". That
was not accurate and was corrected. Encryption happens on the server, so the
server sees the password and the plaintext for the duration of the request.
End-to-end privacy requires client-side encryption.

In addition:

- The service is protected by a single API key; there is no per-user
  authorisation.
- TLS must come from a reverse proxy in front of it (nginx, Caddy).
- Python offers no reliable way to wipe a key from memory.
- Deleted files are not securely wiped from disk.

For a security service, documenting what it does not protect matters as much
as documenting what it does. That is why this section also has its own
heading in the README.
