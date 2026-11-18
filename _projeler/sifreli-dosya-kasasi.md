---
title: "Parolayı saklamadan dosya şifrelemek"
kisa: Dosyaları parolayla şifreleyip saklayan, tek kullanımlık ve süreli indirme destekleyen API servisi.
ozet: "Dosyaları parolayla şifreleyen, tek kullanımlık ve süreli indirme bağlantıları sunan bir API servisi. Yazıda seçilen algoritmaları, parametreleri ve servisin neyi vaat etmediğini ele alıyorum."
date: 2026-09-17
teknolojiler: [Python, FastAPI, cryptography, Argon2id, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/sifreli-dosya-kasasi
kategori: guvenlik
sira: 3
ref: vaultcore
---

Hassas bir dosyayı paylaşmanın en yaygın yolu e-postaya eklemek, en büyük
sakıncası da dosyanın yıllarca bir sunucuda açık hâlde kalması. Bu servis üç
şartı birlikte sağlamak için yazıldı:

- Dosya diske yalnızca şifreli olarak yazılmalı.
- Parola hiçbir yerde saklanmamalı.
- Dosya belirli sayıda indirildikten ya da belirli bir süre geçtikten sonra
  kendiliğinden erişilemez hâle gelmeli.

```bash
curl -X POST http://localhost:8000/api/v1/vault/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@belge.pdf" -F "password=uzun-ve-guclu-parola" \
  -F "max_downloads=1" -F "expires_in_hours=24"
```

## Şifreleme akışı

Parola önce Argon2id ile 256 bitlik bir anahtara dönüştürülüyor. Bu anahtar
AES-256-GCM ile dosyayı şifrelemek için kullanılıyor. Her dosya için ayrı bir
tuz (16 bayt) ve ayrı bir nonce (12 bayt) üretiliyor. Veritabanına tuz, nonce
ve dosya bilgileri yazılıyor; parola ve anahtar yazılmıyor.

```python
def encrypt(plaintext: bytes, password: str, aad: bytes | None = None):
    params = _get_crypto_params()
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt, params)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptionResult(ciphertext=ciphertext, salt=salt, nonce=nonce, params=params)
```

### Neden AES-GCM?

AES-GCM, gizlilik ve bütünlüğü tek işlemde sağlayan bir AEAD kipidir.
AES-CBC kullanılsaydı ayrıca bir MAC eklemek ve doğru sırayla uygulamak
gerekirdi; bu adım uygulama hatalarına açıktır. GCM dolgu (padding)
kullanmadığı için padding oracle saldırılarından etkilenmez ve modern
işlemcilerde donanım desteğiyle çalışır.

Kipin dikkat gerektiren tek noktası aynı anahtarla aynı nonce'un iki kez
kullanılmaması. Servis bu nedenle her şifrelemede `os.urandom` ile yeni bir
nonce üretiyor.

### Neden Argon2id?

Kullanıcı parolalarının entropisi düşüktür. Parola doğrudan anahtar olarak
kullanılırsa saldırgan çok kısa sürede çok sayıda tahmin deneyebilir.
Argon2id her türetmede yüksek miktarda bellek kullanır (bu projede 64 MB, 3
tur, 4 iş parçacığı). Bellek GPU'larda kısıtlı olduğundan paralel tahmin
maliyeti belirgin biçimde artar.

Argon2 parametreleri her dosyayla birlikte saklanıyor. Parametreler ileride
güçlendirildiğinde eski dosyalar kendi parametreleriyle açılmaya devam ediyor.

## Uygulamadaki ayrıntılar

- **Dosya kimliği şifreli veriye bağlı.** Kimlik, AES-GCM'nin ek doğrulanmış
  veri (AAD) alanına giriyor. Veritabanında iki dosyanın şifreli içeriği yer
  değiştirilirse doğrulama başarısız oluyor.
- **Hata mesajları ayırt edilemiyor.** Yanlış parola ve bozulmuş veri aynı
  yanıtı veriyor; böylece dışarıya ek bilgi sızmıyor.
- **İki katmanlı deneme sınırı.** IP başına dakikada 5 indirme denemesi
  yapılabiliyor. Aynı dosyaya 5 yanlış parola girildiğinde dosya 15 dakika
  kilitleniyor; bu ikinci katman farklı IP'lerden gelen denemelere karşı da
  çalışıyor.
- **İndirme sayacı atomik.** Tek kullanımlık bir bağlantıya aynı anda gelen
  iki istekten yalnızca biri başarılı oluyor.
- **Kaynak tüketimi sınırlı.** Yüklemeler parça parça okunuyor ve aynı anda
  çalışan anahtar türetme sayısı sınırlandırılıyor.
- **Temizlik.** Süresi dolan, indirme hakkı biten ya da silinen dosyaların
  şifreli verisi diskten de kaldırılıyor.

## Servisin vaat etmedikleri

Reponun GitHub açıklamasında bir süre "zero-knowledge" ifadesi yer alıyordu.
Bu ifade doğru değildi ve düzeltildi. Şifreleme sunucuda yapıldığı için
sunucu, istek süresince parolayı ve dosyanın açık hâlini görüyor. Uçtan uca
gizlilik için şifrelemenin istemci tarafında yapılması gerekir.

Bunun dışında:

- Servis tek bir API anahtarıyla korunuyor; kullanıcı bazlı yetkilendirme yok.
- TLS, önüne konacak bir ters vekil (nginx, Caddy) ile sağlanmalı.
- Python'da anahtarın bellekten güvenilir biçimde silinmesi mümkün değil.
- Silinen dosyalar için güvenli disk silme (secure wipe) uygulanmıyor.

Bir güvenlik servisinin belgesinde neyi korumadığının açıkça yazılması,
neyi koruduğunun yazılması kadar önemli. Bu bölüm o yüzden README'de de
ayrı bir başlık olarak duruyor.
