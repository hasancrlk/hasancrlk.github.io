# hasancrlk.github.io

Kişisel portföy sitesi: https://hasancrlk.github.io

GitHub Pages bu depoyu Jekyll ile kendisi derler; ayrıca bir derleme adımı yok.

## Yapı

| Yol | Ne |
|---|---|
| `index.html`, `en/index.html` | Türkçe ve İngilizce ana sayfa |
| `_projeler/*.md` | Türkçe proje yazıları → `/projeler/<ad>/` |
| `_projects/*.md` | İngilizce proje yazıları → `/en/projects/<ad>/` |
| `_layouts/`, `_includes/` | Sayfa şablonları |
| `_data/metin.yml` | Arayüz metinleri (iki dil) |
| `assets/stil.css` | Tek stil dosyası, açık/koyu tema |

## Yeni proje eklemek

1. `_projeler/<ad>.md` ve `_projects/<ad>.md` dosyalarını oluştur.
2. İkisine de aynı `ref` değerini ver; dil düğmesi karşı dildeki yazıyı bu
   değerle buluyor.
3. Ön bilgi alanları: `title`, `kisa` (kartta görünen tek cümle), `ozet`
   (yazının girişi), `date`, `teknolojiler`, `repo`, `kategori`
   (`guvenlik` · `backend` · `mobil-web` · `donanim`), `sira`.
4. `main` dalına gönder; site bir iki dakika içinde güncellenir.
