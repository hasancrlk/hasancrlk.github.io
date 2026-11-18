---
title: "Parolayı saklamadan dosya şifrelemek"
kisa: Dosyaları parolayla şifreleyip saklayan, tek kullanımlık ve süreli indirme destekleyen API servisi.
ozet: "Hassas bir dosyayı e-postayla gönderdiğinizde o dosya yıllarca bir sunucuda açık hâlde durur. Ben bunun yerine bir kez indirilince ya da süresi dolunca kendiliğinden kapanan, parolası hiçbir yerde saklanmayan bir kasa yazdım."
date: 2026-09-17
teknolojiler: [Python, FastAPI, cryptography, Argon2id, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/sifreli-dosya-kasasi
kategori: guvenlik
sira: 3
ref: vaultcore
---

Bu servisten üç şey istedim: dosya diske yalnızca şifreli yazılsın, parola
hiçbir yerde saklanmasın ve dosya belirli bir sayıda indirildikten ya da
belirli bir süre geçtikten sonra erişilemez olsun. Kullanımı şöyle:

```bash
curl -X POST http://localhost:8000/api/v1/vault/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@belge.pdf" -F "password=uzun-ve-guclu-parola" \
  -F "max_downloads=1" -F "expires_in_hours=24"
```

## Parola nereye gidiyor?

Hiçbir yere. Parolayı Argon2id ile 256 bitlik bir anahtara çeviriyorum, o
anahtarla da dosyayı AES-256-GCM ile şifreliyorum. Her dosya için ayrı bir
tuz (16 bayt) ve ayrı bir nonce (12 bayt) üretiyorum. Veritabanına tuzu,
nonce'u ve dosya bilgilerini yazıyorum; parolayı ve anahtarı yazmıyorum.

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

AES-GCM gizliliği ve bütünlüğü tek işlemde sağlıyor. AES-CBC seçseydim ayrıca
bir MAC eklemem ve bunları doğru sırada uygulamam gerekecekti; bu da hata
yapmaya açık bir adım. GCM dolgu (padding) kullanmadığı için padding oracle
saldırılarından etkilenmiyor ve modern işlemcilerde donanım desteğiyle
çalışıyor.

Dikkat edilmesi gereken tek nokta aynı anahtarla aynı nonce'u iki kez
kullanmamak. Bu yüzden her şifrelemede `os.urandom` ile yeni bir nonce
üretiyorum.

### Neden parolanın kendisi değil de Argon2id?

İnsanların seçtiği parolalar tahmin edilebilir. Parolayı doğrudan anahtar
olarak kullansaydım saldırgan çok kısa sürede çok sayıda tahmin
deneyebilirdi. Argon2id her türetmede yüksek bellek istiyor; bu projede 64 MB,
3 tur ve 4 iş parçacığı. Bellek GPU'larda kısıtlı olduğu için paralel tahmin
yapmak ciddi şekilde pahalılaşıyor.

Argon2 parametrelerini her dosyayla birlikte saklıyorum. Yarın ayarları
güçlendirsem bile eski dosyalar kendi parametreleriyle açılmaya devam ediyor.

## Gözden kaçabilecek ayrıntılar

- **Dosya kimliğini şifreli veriye bağladım.** Kimlik, AES-GCM'nin ek
  doğrulanmış veri (AAD) alanına giriyor. Biri veritabanında iki dosyanın
  şifreli içeriğinin yerini değiştirirse doğrulama başarısız oluyor.
- **Hata mesajları birbirinden ayırt edilemiyor.** Yanlış parola ile bozuk
  veri aynı cevabı veriyor; dışarıya fazladan bilgi sızmıyor.
- **İki katmanlı deneme sınırı koydum.** IP başına dakikada 5 indirme
  denemesi yapılabiliyor. Aynı dosyaya 5 yanlış parola girilirse dosya 15
  dakika kilitleniyor. İkinci katman, farklı IP'lerden gelen denemelere karşı
  da işe yarıyor.
- **İndirme sayacı atomik.** Tek kullanımlık bir bağlantıya aynı anda iki
  istek gelirse yalnızca biri kazanıyor.
- **Kaynak tüketimini sınırladım.** Yüklemeler parça parça okunuyor, aynı
  anda çalışan anahtar türetme sayısı da sınırlı.
- **Süresi dolan dosyalar diskten de siliniyor.** Yalnızca kayıt değil,
  şifreli verinin kendisi de kalkıyor.

## Bu servis neyi vaat etmiyor?

Bir süre reponun GitHub açıklamasında "zero-knowledge" yazıyordu. Doğru
değildi, düzelttim. Şifrelemeyi sunucu yaptığı için sunucu, istek süresince
parolayı ve dosyanın açık hâlini görüyor. Gerçek uçtan uca gizlilik için
şifrelemenin istemci tarafında yapılması gerekir.

Bunun dışında servis tek bir API anahtarıyla korunuyor, kullanıcı bazlı
yetkilendirme yok. TLS'i önüne koyacağınız bir ters vekil (nginx, Caddy)
sağlamalı. Python'da anahtarı bellekten güvenilir biçimde silmek mümkün değil
ve silinen dosyalar için güvenli disk silme uygulamıyorum. Bunları README'de
de ayrı bir başlık altında yazdım; bir güvenlik aracının neyi korumadığını
bilmek, neyi koruduğunu bilmek kadar önemli.
