---
title: "Parolası saklanmayan dosya kasası: AES-256-GCM ve Argon2id pratikte"
kisa: Dosyaları parolayla şifreleyip saklayan, tek kullanımlık ve süreli indirme destekleyen API servisi.
ozet: "Dosyaları parolayla şifreleyip saklayan bir servis yazdım. Sunucunun diski çalınsa bile parolayı bilmeyen kimse dosyayı açamıyor. Bu yazıda neden bu algoritmaları seçtiğimi ve neyi vaat etmediğimi anlatıyorum."
date: 2026-09-17
teknolojiler: [Python, FastAPI, cryptography, Argon2id, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/sifreli-dosya-kasasi
kategori: guvenlik
sira: 3
ref: vaultcore
---

## Problem

Hassas bir dosyayı birine göndermek istiyorsunuz: bir sözleşme, bir kimlik
fotokopisi. E-postaya eklerseniz yıllarca bir sunucuda durur. İstediğim şey
şuydu: dosya **parolayla şifrelensin**, **bir kez indirilince ya da 24 saat
sonra** kendiliğinden kapansın ve sunucunun diski ele geçirilse bile dosya
okunamasın.

```bash
curl -X POST http://localhost:8000/api/v1/vault/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@belge.pdf" -F "password=uzun-ve-guclu-parola" \
  -F "max_downloads=1" -F "expires_in_hours=24"
```

## Akış

```
Parola ──► Argon2id (64 MB, 3 tur) ◄── 16 bayt rastgele tuz
               │
               ▼
        256 bit anahtar ──► AES-256-GCM ◄── 12 bayt rastgele nonce
                                │
                                ▼
                 şifreli veri + 16 bayt doğrulama etiketi
                     │                      │
                 diskte .enc         veritabanında tuz, nonce
                                     (parola ASLA yok)
```

Kodun kalbi kısa:

```python
def encrypt(plaintext: bytes, password: str, aad: bytes | None = None):
    params = _get_crypto_params()
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt, params)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptionResult(ciphertext=ciphertext, salt=salt, nonce=nonce, params=params)
```

## Neden AES-GCM?

AES-GCM hem gizliliği hem bütünlüğü tek işlemde sağlıyor (AEAD). AES-CBC
kullansaydım ayrıca bir MAC eklemem ve sırasını doğru kurmam gerekirdi. Bu
tam da uygulama hatalarının çıktığı yer. GCM'de dolgu (padding) olmadığı
için padding oracle saldırılarına da doğası gereği bağışık. Modern
işlemcilerde donanım hızlandırması (AES-NI) var.

Tek büyük tehlikesi **aynı nonce'u iki kez kullanmak**. Bu hem gizliliği hem
bütünlüğü bozar. Bu yüzden her dosya için `os.urandom` ile yeni bir nonce
üretiliyor.

## Neden doğrudan parola değil de Argon2id?

İnsanların parolaları düşük entropili. Parolayı doğrudan anahtar olarak
kullanmak saldırgana saniyede milyarlarca deneme imkânı verir. Argon2id her
anahtar türetmede 64 MB bellek istiyor. Bellek GPU'larda kıt olduğu için
paralel deneme maliyeti katlanarak artıyor. Bu ayarlarla bir türetme yaklaşık
250 ms sürüyor.

Argon2 parametreleri **dosya başına** saklanıyor. Yarın ayarları
güçlendirirsem eski dosyalar bozulmuyor, eski parametreleriyle açılıyor.

## Küçük ama önemli kararlar

- **Dosya kimliği şifrelemeye bağlı.** Kimlik, AES-GCM'nin "ek doğrulanmış
  veri" (AAD) alanına giriyor. Veritabanında iki dosyanın şifreli verisini yer
  değiştiren biri doğrulama etiketine takılıyor.
- **Hata mesajları ayırt edilemez.** "Yanlış parola" ile "bozuk veri" aynı
  cevabı veriyor. Ayrı cevap vermek saldırgana bilgi sızdırırdı.
- **İki katmanlı deneme sınırı.** IP başına dakikada 5 deneme. Bunun yanında
  aynı dosyaya 5 yanlış parola girilirse dosya 15 dakika kilitleniyor. İkinci
  katman, farklı IP'lerden gelen dağıtık denemelere karşı da çalışıyor.
- **İndirme sayacı yarışa dayanıklı.** Tek kullanımlık bir bağlantıya aynı
  anda iki istek gelirse yalnızca biri kazanıyor. Sayaç atomik olarak
  artırılıyor.
- **Bellek tüketimine karşı önlem.** Yükleme parça parça okunuyor ve aynı anda
  çalışan anahtar türetme sayısı sınırlı. Aksi halde 64 MB'lık türetmeler
  sunucuyu kolayca tüketirdi.

## Neyi vaat etmiyorum

Reponun GitHub açıklamasında bir süre "zero-knowledge" yazıyordu. Doğru
değildi, düzelttim.
Şifreleme **sunucuda** yapılıyor, yani sunucu istek süresince parolayı ve
dosyanın açık hâlini görüyor. Gerçek uçtan uca gizlilik için şifrelemenin
istemcide yapılması gerekir. Ayrıca servis tek bir API anahtarıyla
korunuyor, kullanıcı bazlı yetkilendirme yok ve TLS bir ters vekil
(nginx/Caddy) üzerinden sağlanmalı.

## Öğrendiklerim

Kriptografide algoritma seçmek işin küçük kısmı. Asıl iş tuzu, nonce'u,
parametreleri ve hata mesajlarını doğru yönetmek. Bir de vaadi doğru yazmak:
"zero-knowledge" demek kulağa iyi geliyordu ama yanlıştı. Bir güvenlik
ürününde abartılı bir iddia, eksik bir özellikten daha zararlı.
