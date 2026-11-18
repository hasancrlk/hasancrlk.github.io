---
title: "Başlık var ama korumuyor: web güvenlik başlıklarına A–F notu veren tarayıcı"
kisa: Web sitelerinin güvenlik başlıklarını değerleriyle birlikte puanlayan, eksikler için hazır satır öneren tarayıcı.
ozet: "Web sitelerinin güvenlik başlıklarını kontrol edip A–F arası not veren bir tarayıcı yazdım. Başlığın var olup olmadığına değil, gerçekten koruyup korumadığına bakıyor."
date: 2026-09-18
teknolojiler: [Python, httpx, FastAPI, SQLAlchemy, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/http-guvenlik-basligi-tarayici
kategori: guvenlik
sira: 6
ref: headerguard
---

## Problem

Bir web sitesi her sayfayla birlikte tarayıcıya görünmeyen güvenlik başlıkları
gönderir: "bu siteyi yalnızca HTTPS ile aç" (HSTS), "yalnızca şu kaynaklardan
script yükle" (CSP), "sayfamı başka sitenin içine gömme" (X-Frame-Options).
Eksik ya da yanlış olduklarında site çalışmaya devam eder. Sorun ancak bir
saldırı olunca görünür.

Var olan birçok kontrol aracı yalnızca "başlık var mı?" diye bakıyor. Bu da şu
yapılandırmaya iyi not veriyor:

```
Strict-Transport-Security: max-age=1
```

Başlık **var**. Ve tam olarak bir saniye boyunca koruyor, yani korumuyor.

## Zor kısım 1: Var/yok yerine oran

Her başlığın alt kontrolleri var ve başarısız her kontrol başlığın puan oranını
düşürüyor:

| Başlık | Değer | Oran | Neden |
|---|---|---|---|
| HSTS | `max-age=31536000; includeSubDomains` | 1.00 | Tam |
| HSTS | `max-age=31536000` | 0.80 | Alt alan adları korumasız |
| HSTS | `max-age=60` | 0.50 | 6 aydan kısa |
| CSP | `default-src 'self'; script-src 'unsafe-inline'` | 0.60 | XSS korumasında delik |

Toplam puan ağırlıklı ortalamadan geliyor. En ağır başlıklar CSP (22) ve HSTS
(18). Sürüm sızdıran `Server: nginx/1.24.0`, `X-Powered-By` ve
`Access-Control-Allow-Origin: *` gibi başlıklar ceza puanı alıyor.

İki özel durumu ayrıca düşündüm:

- **Düz HTTP sitede HSTS eksikliği ayrıca cezalandırılmıyor.** Asıl sorun
  HTTP'nin kendisi ve o ayrı, yüksek önemli bir bulgu. Aynı eksikliği iki kez
  saymak notu yapay biçimde düşürürdü.
- **`X-Frame-Options` yok ama CSP'de `frame-ancestors` varsa tam puan.**
  Modern ve doğru yapılandırmayı eski başlığı taşımadığı için cezalandırmak
  yanlış olurdu.

## Zor kısım 2: Kurallar kodda değil, dosyada

Kurallar `data/rules.json` dosyasında duruyor. Kurum kendi politikasını
yazabiliyor, kod değişmiyor:

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

Burada bir güvenlik sorusu var: esnek bir kural dosyası, onu değiştirebilen
birine **kod çalıştırma** imkânı vermemeli. Bu yüzden kontrol tipleri sabit
bir kümeden seçiliyor. Tanınmayan bir tip dosyayı reddettiriyor, sessizce
atlanmıyor. Düzenli ifadeler açılışta derleniyor ve hiçbir `eval` yolu yok.

Yürürlükteki kurallar `GET /rules` ile okunabiliyor. Hesaplanma biçimi
görülemeyen bir not tartışılamaz da. "Neden C aldık?" sorusunun cevabı elde
olmalı.

## Zor kısım 3: Yönlendirmeler

Yönlendirmeleri `httpx`'in otomatik takibine bırakmadım, elle izliyorum.
Otomatik takipte yalnızca son yanıtın başlıkları görünüyor. Oysa zincirin
kendisi bir bulgu:

```
http://site.com → https://site.com → https://www.site.com
                                      ↑ HSTS burada var, ama ilk istek düz HTTP'ydi
```

`https://` ile başlayıp `http://` ile biten bir zincir **protokol düşürme**
olarak yüksek önemle raporlanıyor. Erişilemeyen bir hedef taramayı çökertmiyor.
Her hedef ayrı değerlendiriliyor ve sonuçta hata türüyle görünüyor.

## Çerezler, TLS ve fark raporu

Çerezlerde `Secure`, `HttpOnly` ve `SameSite` bayrakları kontrol ediliyor. TLS
sertifikasının sahibi, yayıncısı ve bitmesine kaç gün kaldığı raporlanıyor.
İki taramayı karşılaştıran bir rapor da var. Burada bir tuzağı kapattım:
listeden çıkarılan kötü bir site ortalamayı yükselttiği için "iyileşme" gibi
görünmesin diye yalnızca iki taramada da bulunan hedefler karşılaştırılıyor.

## Bilerek yapmadıklarım

Yalnızca sitenin kök sayfası taranıyor. JavaScript çalıştırılmıyor, bu yüzden
`<meta>` ile verilen CSP görülmüyor. CSP analizi yüzeysel: `unsafe-inline`
yakalanıyor ama nonce/hash stratejisi değerlendirilmiyor. En önemlisi: **A
alan bir site güvenli demek değil.** Başlıklar savunmanın yalnızca bir katmanı.

## Öğrendiklerim

Puanlama sistemi tasarlamak teknik bir iş olduğu kadar adalet işi. Her kural
"bu yapılandırmayı yanlışlıkla cezalandırır mı ya da ödüllendirir mi?"
sorusundan geçmeli. Bir de şunu öğrendim: yapılandırılabilirlik bir saldırı
yüzeyi açar. Esnekliği kod çalıştırmaya dönüşmeyecek şekilde sınırlamak
gerekir.
