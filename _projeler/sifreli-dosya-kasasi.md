---
title: "Parolayı Saklamadan Dosya Şifrelemek: AES-256-GCM ve Argon2id"
kisa: Dosyaları parolayla şifreleyip saklayan, one-time ve süreli download destekleyen bir API servisi.
ozet: "Bir dosyayı şifrelemek için doğru algoritmayı seçmek işin küçük kısmı. Asıl iş salt, nonce, KDF parametreleri ve hata mesajları gibi ayrıntıları doğru yönetmekte."
date: 2026-09-17
teknolojiler: [Python, FastAPI, cryptography, Argon2id, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/sifreli-dosya-kasasi
kategori: guvenlik
sira: 3
ref: vaultcore
---

Hassas bir dosyayı e-postayla paylaştığınızda o dosya yıllarca bir sunucuda
plaintext olarak durur. VaultCore'u bunun yerine üç gereksinimi birlikte
karşılamak için geliştirdim: dosya diske yalnızca şifreli yazılmalı, parola
hiçbir yerde saklanmamalı ve dosya belirli sayıda download'dan ya da belirli bir
süreden sonra erişilemez olmalı.

Bu yazıda servisin kriptografik tasarımını, verdiğim kararların gerekçelerini ve
servisin neyi vaat etmediğini anlatıyorum.

```bash
curl -X POST http://localhost:8000/api/v1/vault/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@belge.pdf" -F "password=uzun-ve-guclu-parola" \
  -F "max_downloads=1" -F "expires_in_hours=24"
```

## Şifreleme akışı

Parola önce Argon2id ile 256 bitlik bir key'e dönüştürülüyor, bu key ile dosya
AES-256-GCM kullanılarak şifreleniyor. Her dosya için ayrı bir salt (16 byte) ve
ayrı bir nonce (12 byte) üretiliyor. Veritabanına salt, nonce ve metadata
yazılıyor; parola ve key yazılmıyor.

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

AES-GCM bir AEAD (Authenticated Encryption with Associated Data) modu; gizliliği
ve bütünlüğü tek işlemde sağlıyor. AES-CBC seçseydim ayrıca bir MAC eklemem ve
encrypt-then-MAC sırasını doğru uygulamam gerekirdi; implementasyon hatalarının
çıktığı yer tam olarak burası. GCM padding kullanmadığı için padding oracle
saldırılarından etkilenmiyor ve modern CPU'larda AES-NI ile donanım
hızlandırması var.

Dikkat edilmesi gereken tek nokta **nonce reuse**: aynı key ile aynı nonce'un iki
kez kullanılması hem gizliliği hem bütünlüğü bozar. Bu yüzden her şifrelemede
`os.urandom` ile yeni bir nonce üretiliyor.

## Neden Argon2id?

Kullanıcı parolalarının entropisi düşüktür. Parola doğrudan key olarak
kullanılırsa saldırgan saniyede çok sayıda tahmin deneyebilir. Argon2id
memory-hard bir KDF: bu projede her türetme 64 MB bellek, 3 iterasyon ve 4 thread
kullanıyor. GPU'larda bellek kısıtlı olduğu için paralel brute-force maliyeti
ciddi şekilde artıyor.

Argon2 parametreleri dosya başına saklanıyor. Parametreler ileride
güçlendirilirse eski dosyalar kendi parametreleriyle açılmaya devam ediyor.

## Gözden kaçabilecek ayrıntılar

- **Dosya ID'si ciphertext'e bağlı.** ID, AES-GCM'nin AAD alanına giriyor.
  Veritabanında iki dosyanın ciphertext'i yer değiştirilirse authentication tag
  doğrulaması başarısız oluyor.
- **Hata mesajları ayırt edilemiyor.** Yanlış parola ile bozulmuş veri aynı
  response'u dönüyor; oracle saldırılarına açık kapı bırakılmıyor.
- **İki katmanlı rate limiting.** IP başına dakikada 5 download denemesi; aynı
  dosyaya 5 yanlış parola girilirse dosya 15 dakika kilitleniyor. İkinci katman
  farklı IP'lerden gelen dağıtık denemelere karşı da çalışıyor.
- **Atomik download sayacı.** One-time bir link'e aynı anda iki istek gelirse
  yalnızca biri başarılı oluyor; race condition yok.
- **DoS'a karşı sınırlar.** Upload chunk'lar hâlinde okunuyor ve eşzamanlı KDF
  sayısı sınırlı; 64 MB'lık türetmeler sunucuyu tüketmiyor.
- **Cleanup.** Süresi dolan ya da download hakkı biten dosyaların ciphertext'i
  diskten de siliniyor.

## Servisin vaat etmedikleri

Bir süre reponun GitHub açıklamasında "zero-knowledge" yazıyordu. Doğru değildi,
düzelttim. Şifreleme server-side yapılıyor; yani sunucu, istek süresince parolayı
ve dosyanın plaintext hâlini görüyor. Gerçek end-to-end gizlilik için şifrelemenin
client-side yapılması gerekir.

Diğer sınırlar: servis tek bir API key ile korunuyor, kullanıcı bazlı
authorization yok; TLS bir reverse proxy (nginx, Caddy) ile sağlanmalı; Python'da
key'i bellekten güvenilir biçimde silmek mümkün değil; silinen dosyalar için
secure wipe yapılmıyor.

## Kapanış

Kriptografi kullanan bir serviste algoritma seçimi genellikle tartışılan kısım
oluyor, ama hatalar çoğunlukla çevresindeki ayrıntılarda çıkıyor: nonce yönetimi,
KDF parametreleri, hata mesajları, rate limiting. Bir güvenlik servisinin neyi
korumadığını açıkça yazmak da en az neyi koruduğunu yazmak kadar önemli;
abartılmış bir iddia, eksik bir özellikten daha fazla zarar verir.
