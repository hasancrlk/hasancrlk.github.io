---
title: "HTTP Security Header'ları Neden Sadece \"Var mı?\" Diye Kontrol Edilmemeli"
kisa: Web sitelerinin HTTP security header'larını değerleriyle birlikte puanlayan, A–F not veren bir scanner.
ozet: "Bir security header'ın response'ta bulunması, sitenin korunduğu anlamına gelmez. max-age=1 olan bir HSTS header'ı kâğıt üzerinde vardır, pratikte hiçbir şey korumaz."
date: 2026-09-18
teknolojiler: [Python, httpx, FastAPI, SQLAlchemy, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/http-guvenlik-basligi-tarayici
kategori: guvenlik
sira: 6
ref: headerguard
---

Bir web sunucusu her response ile birlikte tarayıcıya bazı security header'lar
gönderir: `Strict-Transport-Security` (HSTS), `Content-Security-Policy` (CSP),
`X-Frame-Options` gibi. Bu header'lar tarayıcıya "bu siteyi yalnızca HTTPS ile
aç", "yalnızca şu kaynaklardan script yükle", "sayfamı başka bir sitenin içine
frame olarak gömme" der. Eksik ya da yanlış yapılandırıldıklarında site çalışmaya
devam eder; sorun ancak bir saldırı anında görünür.

Bu yazıda HeaderGuard adını verdiğim scanner'ı anlatıyorum. EMT Cyber stajında
verilen ödevlerden biriydi. Amacım header'ların yalnızca varlığına değil,
değerlerinin gerçekten koruma sağlayıp sağlamadığına bakan bir puanlama
yapmaktı.

## Varlık kontrolünün sorunu

Şu satır geçerli bir HTTP response header'ıdır:

```
Strict-Transport-Security: max-age=1
```

Sadece varlığa bakan bir kontrol bu siteyi geçer sayar. Oysa `max-age=1`,
tarayıcıya HSTS kuralını yalnızca bir saniye hatırlamasını söyler. Kâğıt
üzerinde A alan ama pratikte korumayan yapılandırmalar tam olarak böyle ortaya
çıkar.

## Puanlama nasıl çalışıyor?

Her header'ın bir ağırlığı ve bir dizi alt kontrolü var. Başarısız olan her
kontrol, o header'ın puan oranını düşürüyor. Toplam skor oranların ağırlıklı
ortalamasından hesaplanıyor, ardından penalty puanları düşülüyor ve sonuç A–F
notuna çevriliyor.

Ağırlıkları header'ların korumadaki rolüne göre belirledim:

- **Content-Security-Policy (22).** XSS'in etkisini sınırlamada en güçlü tek
  header.
- **Strict-Transport-Security (18).** SSL stripping ve HTTPS→HTTP downgrade
  saldırılarını kapatır.
- **X-Frame-Options (10).** Clickjacking'e karşı.
- **X-Content-Type-Options ve Referrer-Policy (8'er).** MIME sniffing ve URL
  sızıntısı.

Alt kontrollere birkaç örnek:

- `max-age=31536000; includeSubDomains` → HSTS tam puan alır.
- `max-age=31536000` → subdomain'ler korumasız kaldığı için oran 0,80.
- `max-age=60` → altı aydan kısa olduğu için oran 0,50.
- `script-src 'unsafe-inline'` içeren bir CSP → oran 0,60.

Bilgi sızdıran header'lar ise penalty alıyor: sürüm numarası veren
`Server: nginx/1.24.0`, `X-Powered-By` ve `Access-Control-Allow-Origin: *`.

İki durumu ayrıca ele aldım. Düz HTTP üzerinden sunulan bir sitede HSTS eksikliği
ayrıca cezalandırılmıyor; asıl sorun HTTP'nin kendisi ve o zaten ayrı, yüksek
önemli bir finding olarak raporlanıyor. CSP'de `frame-ancestors` tanımlıysa da
`X-Frame-Options` eksikliği puan kaybettirmiyor, çünkü modern ve doğru
yapılandırma bu.

## Kurallar kodda değil, config dosyasında

Puanlama kuralları `data/rules.json` içinde duruyor. Bir kurum kendi
politikasını kodu değiştirmeden tanımlayabiliyor:

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

Burada bir güvenlik sorusu var: esnek bir config dosyası, onu değiştirebilen
birine code execution imkânı vermemeli. Bu yüzden check tipleri sabit bir
kümeyle sınırlı; tanınmayan bir tip dosyanın yüklenmesini durduruyor. Regex'ler
uygulama açılırken derleniyor ve hiçbir `eval` yolu yok. Aktif kurallar
`GET /rules` endpoint'inden okunabiliyor; bir notun nasıl hesaplandığı her zaman
görülebilmeli.

## Redirect zincirini elle takip etmek

Redirect'leri `httpx`'in otomatik takibine bırakmadım. Otomatik takipte yalnızca
son response'un header'ları görünür, oysa zincirin kendisi bir finding olabilir:

```
http://site.com → https://site.com → https://www.site.com
```

HSTS son adımda olsa bile ilk istek düz HTTP üzerinden gitmiştir. `https://` ile
başlayıp `http://` ile biten bir zincir **protocol downgrade** olarak yüksek
önemle raporlanıyor. 10'dan fazla redirect loop kabul ediliyor. Erişilemeyen bir
hedef de taramanın tamamını durdurmuyor; her hedef ayrı değerlendiriliyor.

## Cookie, TLS ve karşılaştırma raporu

Cookie'lerde `Secure`, `HttpOnly` ve `SameSite` flag'leri kontrol ediliyor. TLS
sertifikasının subject, issuer ve bitişine kalan gün bilgisi raporlanıyor. İki
taramayı karşılaştıran bir diff raporu da var. Burada yalnızca iki taramada da
bulunan hedefler hesaba katılıyor; listeden kötü skorlu bir siteyi çıkarmak
ortalamayı yükseltip "iyileşme" gibi görünmesin diye.

## Kapanış

HeaderGuard'ın sınırları belli: yalnızca kök sayfayı tarıyor, JavaScript
çalıştırmadığı için `<meta>` ile verilen CSP'yi görmüyor, CSP analizinde nonce
ve hash stratejilerini değerlendirmiyor. Yüksek bir not sitenin güvenli olduğu
anlamına da gelmiyor; security header'lar savunmanın yalnızca bir katmanı. Ama
"header var mı?" yerine "header gerçekten koruyor mu?" sorusunu sormak, hızlı
bir ilk değerlendirme için çok daha anlamlı bir sonuç veriyor.

Proje 53 testle geliyor ve `docker compose up` ile PostgreSQL ile birlikte
çalışıyor.

*Bu araç yalnızca sahibi olduğunuz ya da test izni verilmiş sistemlerde
kullanılmalıdır.*
