---
title: "Güvenlik başlıklarını değerleriyle puanlamak"
kisa: Web sitelerinin güvenlik başlıklarını değerleriyle birlikte puanlayan, eksikler için hazır satır öneren tarayıcı.
ozet: "\"Strict-Transport-Security: max-age=1\" geçerli bir başlık. Varlığına bakan bir kontrol bu siteyi başarılı sayar. Oysa bu başlık tarayıcıya kuralı tam bir saniye hatırlamasını söylüyor."
date: 2026-09-18
teknolojiler: [Python, httpx, FastAPI, SQLAlchemy, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/http-guvenlik-basligi-tarayici
kategori: guvenlik
sira: 6
ref: headerguard
---

HeaderGuard'ı tam olarak bu tür durumları yakalamak için yazdım. Bir siteye
istek atıyor, dönen güvenlik başlıklarını inceliyor ve 0–100 arası bir puanla
A–F arası bir not veriyor. Başlık var mı diye değil, gerçekten koruyor mu diye
bakıyor.

## Puanı nasıl hesaplıyorum?

Her başlığın bir ağırlığı ve bir dizi alt kontrolü var. Başarısız olan her
kontrol başlığın puan oranını düşürüyor. Toplam puan, bu oranların ağırlıklı
ortalamasından ceza puanlarının çıkarılmasıyla bulunuyor.

Ağırlıkları her başlığın korumadaki rolüne göre belirledim:

- **Content-Security-Policy (22):** XSS'in etkisini sınırlayan en güçlü
  başlık.
- **Strict-Transport-Security (18):** HTTPS'ten HTTP'ye düşürme saldırılarını
  kapatıyor.
- **X-Frame-Options (10):** Sayfanın başka bir sitede çerçeveye alınmasını,
  yani clickjacking'i engelliyor.
- **X-Content-Type-Options ve Referrer-Policy (8'er):** MIME tahmini ve adres
  sızıntısı.

Birkaç örnek vereyim:

- `max-age=31536000; includeSubDomains` → HSTS tam puan alıyor.
- `max-age=31536000` → alt alan adları korumasız kaldığı için 0,80.
- `max-age=60` → altı aydan kısa olduğu için 0,50.
- `script-src 'unsafe-inline'` içeren bir CSP → 0,60.

Sürüm bilgisi veren `Server: nginx/1.24.0`, `X-Powered-By` ve
`Access-Control-Allow-Origin: *` gibi başlıklar ceza puanı alıyor.

İki durumu ayrıca düşündüm. Düz HTTP üzerinden sunulan bir sitede HSTS
eksikliğini ayrıca cezalandırmıyorum; asıl sorun HTTP'nin kendisi ve o zaten
ayrı, yüksek önemli bir bulgu. CSP'de `frame-ancestors` tanımlıysa da
`X-Frame-Options` eksikliği puan kaybettirmiyor. Modern ve doğru yapılandırmayı
eski bir başlığı taşımıyor diye cezalandırmak bana yanlış geldi.

## Kuralları koda değil dosyaya yazdım

Puanlama kuralları `data/rules.json` dosyasında duruyor. Bir kurum kendi
politikasını kod değiştirmeden tanımlayabiliyor:

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

Burada bir güvenlik sorusu çıkıyor: esnek bir kural dosyası, onu
değiştirebilen birine kod çalıştırma imkânı vermemeli. Bu yüzden kontrol
tiplerini sabit bir kümeyle sınırladım; tanınmayan bir tip dosyanın
yüklenmesini durduruyor. Düzenli ifadeler uygulama açılırken derleniyor ve
hiçbir `eval` yolu yok. Yürürlükteki kuralları `GET /rules` ile
görebiliyorsunuz. "Neden C aldık?" sorusunun cevabı her zaman ortada olsun
istedim.

## Yönlendirmeleri neden elle takip ediyorum?

`httpx`'in otomatik takibinde yalnızca son yanıtın başlıkları görünüyor. Oysa
zincirin kendisi bir bulgu olabilir. `https://` ile başlayıp `http://` ile
biten bir zinciri **protokol düşürme** olarak yüksek önemle raporluyorum. On
yönlendirmeyi aşan zincirleri döngü sayıyorum. Erişilemeyen bir hedef de
taramanın tamamını durdurmuyor; her hedef ayrı değerlendiriliyor.

## Çerezler, TLS ve karşılaştırma

Çerezlerde `Secure`, `HttpOnly` ve `SameSite` bayraklarına, TLS sertifikasında
sahibine, yayıncısına ve bitmesine kaç gün kaldığına bakıyorum. İki taramayı
karşılaştırırken yalnızca iki taramada da bulunan hedefleri hesaba katıyorum;
listeden kötü bir siteyi çıkarmak ortalamayı yükseltip iyileşme gibi
görünmesin diye.

## Sınırlar

Yalnızca sitenin kök sayfasını tarıyorum ve JavaScript çalıştırmıyorum, bu
yüzden `<meta>` ile verilen bir CSP'yi göremiyorum. CSP analizi
`unsafe-inline` ve `default-src *` gibi açık zayıflıkları yakalıyor ama nonce
ve hash stratejilerini değerlendirmiyor. Şunu da eklemeliyim: yüksek bir not,
sitenin güvenli olduğu anlamına gelmiyor. Başlıklar savunmanın yalnızca bir
katmanı.

Proje 53 testle geliyor.
