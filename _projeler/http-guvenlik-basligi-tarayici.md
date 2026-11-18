---
title: "Güvenlik başlıklarını değerleriyle puanlamak"
kisa: Web sitelerinin güvenlik başlıklarını değerleriyle birlikte puanlayan, eksikler için hazır satır öneren tarayıcı.
ozet: "Web sitelerinin HTTP güvenlik başlıklarını inceleyip 0–100 arası puan ve A–F arası not veren bir tarayıcı. Başlığın yalnızca var olup olmadığına değil, değerinin gerçekten koruma sağlayıp sağlamadığına bakıyor."
date: 2026-09-18
teknolojiler: [Python, httpx, FastAPI, SQLAlchemy, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/http-guvenlik-basligi-tarayici
kategori: guvenlik
sira: 6
ref: headerguard
---

Aşağıdaki satır geçerli bir HTTP yanıt başlığıdır:

```
Strict-Transport-Security: max-age=1
```

Başlık mevcut olduğu için yalnızca varlığına bakan bir kontrol bu siteyi
başarılı sayar. Oysa `max-age=1`, tarayıcıya bu kuralı yalnızca bir saniye
hatırlamasını söyler. HeaderGuard bu tür durumları ayırt etmek için yazıldı.

## Puanlama

Her başlık için bir ağırlık ve bir dizi alt kontrol tanımlı. Başarısız olan
her kontrol başlığın puan oranını düşürüyor. Toplam puan, oranların ağırlıklı
ortalamasından ve ceza puanlarından oluşuyor.

En yüksek ağırlıklar, korumadaki rollerine göre belirlendi:

- **Content-Security-Policy (22):** XSS etkisini sınırlayan en güçlü başlık.
- **Strict-Transport-Security (18):** HTTPS'ten HTTP'ye düşürme saldırılarını
  engeller.
- **X-Frame-Options (10):** Sayfanın başka bir sitede çerçeve içine
  alınmasını, yani clickjacking'i engeller.
- **X-Content-Type-Options ve Referrer-Policy (8'er):** MIME tahmini ve
  adres sızıntısı.

Bazı örnekler:

- `max-age=31536000; includeSubDomains` → HSTS tam puan alır.
- `max-age=31536000` → alt alan adları korumasız kaldığı için oran 0,80.
- `max-age=60` → süre altı aydan kısa olduğu için oran 0,50.
- `script-src 'unsafe-inline'` içeren bir CSP → oran 0,60.

Sürüm bilgisi veren `Server: nginx/1.24.0`, `X-Powered-By` ve
`Access-Control-Allow-Origin: *` gibi başlıklar ise ceza puanı alıyor.

İki durum özel olarak ele alındı. Düz HTTP üzerinden sunulan bir sitede HSTS
eksikliği ayrıca cezalandırılmıyor; asıl sorun HTTP kullanımının kendisi ve o
ayrı bir yüksek önemli bulgu olarak raporlanıyor. CSP'de `frame-ancestors`
tanımlıysa `X-Frame-Options` eksikliği puan kaybettirmiyor, çünkü modern
yapılandırma bu.

## Kurallar kodda değil, dosyada

Puanlama kuralları `data/rules.json` dosyasında tutuluyor. Bir kurum kendi
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

Yapılandırılabilir bir dosyanın, onu değiştirebilen birine kod çalıştırma
imkânı vermemesi gerekiyor. Bu nedenle kontrol tipleri sabit bir kümeden
seçiliyor ve tanınmayan bir tip dosyanın yüklenmesini durduruyor. Düzenli
ifadeler uygulama açılırken derleniyor; herhangi bir `eval` yolu bulunmuyor.
Yürürlükteki kurallar `GET /rules` ucundan okunabiliyor, böylece verilen
notun nasıl hesaplandığı her zaman görülebiliyor.

## Yönlendirmeler

Yönlendirmeler `httpx`'in otomatik takibine bırakılmadı, elle izleniyor.
Otomatik takipte yalnızca son yanıtın başlıkları görülür; oysa zincirin
kendisi bir bulgu olabilir. `https://` ile başlayıp `http://` ile biten bir
zincir **protokol düşürme** olarak yüksek önemle raporlanıyor. 10'dan fazla
yönlendirme döngü olarak kabul ediliyor.

Erişilemeyen bir hedef taramanın tamamını durdurmuyor; her hedef ayrı
değerlendiriliyor ve sonuçta hata türüyle görünüyor.

## Çerezler, TLS ve karşılaştırma

Çerezlerde `Secure`, `HttpOnly` ve `SameSite` bayrakları kontrol ediliyor.
TLS sertifikasının sahibi, yayıncısı ve bitmesine kalan gün sayısı
raporlanıyor. İki tarama karşılaştırılırken yalnızca her iki taramada da
bulunan hedefler hesaba katılıyor; listeden çıkarılan bir hedefin ortalamayı
yükseltip iyileşme gibi görünmesi bu şekilde önleniyor.

## Sınırlar

Yalnızca sitenin kök sayfası taranıyor ve JavaScript çalıştırılmıyor; bu
nedenle `<meta>` etiketiyle verilen CSP görülmüyor. CSP analizi `unsafe-inline`
ve `default-src *` gibi açık zayıflıkları yakalıyor, nonce ve hash
stratejilerini değerlendirmiyor. Yüksek bir not sitenin güvenli olduğu
anlamına gelmiyor; başlıklar savunmanın yalnızca bir katmanı.

Proje 53 testle birlikte geliyor.
