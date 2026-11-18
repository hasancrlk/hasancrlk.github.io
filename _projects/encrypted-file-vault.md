---
title: "A file vault that never stores the password: AES-256-GCM and Argon2id in practice"
kisa: An API service that encrypts files with a password and supports one-time and time-limited downloads.
ozet: "I built a service that encrypts and stores files with a password. Even if the server's disk is stolen, nobody without the password can open them. This post covers why I picked these algorithms and what the service does not promise."
date: 2026-09-17
teknolojiler: [Python, FastAPI, cryptography, Argon2id, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/sifreli-dosya-kasasi
kategori: guvenlik
sira: 3
ref: vaultcore
---

## The problem

You want to send someone a sensitive file: a contract, a copy of an ID. Attach
it to an email and it sits on a server for years. What I wanted: the file is
**encrypted with a password**, it **expires after one download or 24 hours**,
and it stays unreadable even if the server's disk is compromised.

```bash
curl -X POST http://localhost:8000/api/v1/vault/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@contract.pdf" -F "password=long-and-strong-passphrase" \
  -F "max_downloads=1" -F "expires_in_hours=24"
```

## The flow

```
Password ──► Argon2id (64 MB, 3 passes) ◄── 16-byte random salt
                 │
                 ▼
          256-bit key ──► AES-256-GCM ◄── 12-byte random nonce
                              │
                              ▼
               ciphertext + 16-byte authentication tag
                   │                       │
              .enc on disk          salt, nonce in the database
                                    (the password NEVER)
```

The core is short:

```python
def encrypt(plaintext: bytes, password: str, aad: bytes | None = None):
    params = _get_crypto_params()
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt, params)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptionResult(ciphertext=ciphertext, salt=salt, nonce=nonce, params=params)
```

## Why AES-GCM?

AES-GCM gives confidentiality and integrity in one operation (AEAD). With
AES-CBC I would have to add a MAC myself and get the order right, which is
exactly where implementation bugs live. GCM has no padding, so it is immune to
padding-oracle attacks by design, and modern CPUs accelerate it (AES-NI).

Its one big danger is **reusing a nonce**, which breaks both confidentiality
and integrity. That is why every file gets a fresh nonce from `os.urandom`.

## Why Argon2id instead of the password itself?

Human passwords have low entropy. Using one directly as a key would let an
attacker try billions of guesses per second. Argon2id needs 64 MB of memory
for every derivation. Memory is scarce on GPUs, so parallel guessing becomes
far more expensive. With these settings one derivation takes about 250 ms.

Argon2 parameters are stored **per file**. If I strengthen the settings
tomorrow, old files still open with their original parameters.

## Small but important decisions

- **The file ID is bound to the ciphertext.** It goes into AES-GCM's
  associated data (AAD). Swapping two files' ciphertexts in the database
  fails the authentication tag.
- **Errors are indistinguishable.** "Wrong password" and "corrupted data"
  return the same response. Different answers would leak information.
- **Two layers of rate limiting.** 5 attempts per minute per IP, and a file
  is locked for 15 minutes after 5 wrong passwords. The second layer also
  stops distributed guessing from many IPs.
- **Race-free download counter.** If two requests hit a one-time link at the
  same moment, only one wins. The counter is incremented atomically.
- **Memory exhaustion guards.** Uploads are read in chunks and the number of
  concurrent key derivations is capped. Otherwise 64 MB derivations would
  take the server down easily.

## What it does not promise

For a while the GitHub description said "zero-knowledge". That was wrong and
I corrected it. Encryption happens **on the server**, so the server sees the
password and the plaintext during the request. True end-to-end privacy needs
client-side encryption. The service is also protected by a single API key,
there is no per-user authorisation, and TLS should come from a reverse proxy
(nginx/Caddy).

## What I learned

Choosing the algorithm is the small part of cryptography. The real work is
handling the salt, the nonce, the parameters and the error messages correctly.
And stating the promise correctly: "zero-knowledge" sounded good but was
false. In a security product, an overstated claim does more harm than a
missing feature.
