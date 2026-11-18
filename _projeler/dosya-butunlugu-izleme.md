---
title: "Staja başlarken adını bilmediğim bir araç: dosya bütünlüğü izleme"
kisa: Bir klasörün imzalı parmak izini alıp sonradan değişen, eklenen ve silinen dosyaları bulan adli bilişim aracı.
ozet: "Dosya bütünlüğü izleme (FIM) kavramıyla stajda tanıştım. Bu yazı, sonradan değişen dosyaları bulan aracı ve aracın kendi kayıtlarını kurcalanmaya karşı nasıl koruduğunu anlatıyor."
date: 2026-09-17
teknolojiler: [Python, FastAPI, SQLAlchemy, Alembic, Typer, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/dosya-butunlugu-izleme
kategori: guvenlik
sira: 2
ref: fim-sentinel
---

EMT Cyber'deki stajıma başlarken "File Integrity Monitoring" ifadesini daha önce
duymamıştım. Ödev olarak verildiğinde ilk iş kavramın ne olduğunu ve neden bu
kadar yaygın kullanıldığını anlamak oldu.

## Kavram

Bir sunucuya sızan saldırgan çoğu zaman dosya sisteminde iz bırakır: bir
sayfaya zararlı kod ekler, bir arka kapı dosyası yükler ya da bir
yapılandırma dosyasını değiştirir. Dosya bütünlüğü izleme bu değişiklikleri
yakalamak için iki adımlı bir yöntem kullanır:

1. Klasörün güvenilir hâlinin parmak izi alınır. Buna **temel kayıt**
   (baseline) denir.
2. Klasör belirli aralıklarla yeniden taranır ve temel kayıtla karşılaştırılır.

Aracın komut satırındaki karşılığı şöyle:

```
$ python -m cli.fim_cli baseline --path /var/www/html
$ python -m cli.fim_cli scan --baseline-id 1

│ MODIFIED │ /var/www/html/index.html │ Hash mismatch detected. │
│ MODIFIED │ /var/www/html/config.php │ Hash mismatch detected. │
│ ADDED    │ /var/www/html/shell.php  │ New file detected.      │
```

Her dosya için SHA-256 özeti, boyut, izinler ve sahiplik bilgisi tutuluyor.
Dosyalar 64 KB'lık parçalar hâlinde okunduğu için büyük dosyalar belleği
zorlamıyor.

## Asıl soru: kayıtların kendisi

Karşılaştırma ne kadar doğru olursa olsun, temel kayıt veritabanında
duruyor. Veritabanına erişen bir saldırgan, eklediği `shell.php` dosyasını
temel kayda da ekleyebilir; bu durumda tarama hiçbir değişiklik göstermez.

Adli bilişimde bu soru **delil zinciri** (chain of custody) kavramıyla
karşılanır: delilin toplandığı andan itibaren değiştirilmediğinin
kanıtlanabilmesi. Araçta bunun için şu önlemler var:

**Temel kayıt imzalanıyor.** Her temel kayıt `FIM_HMAC_KEY` ile HMAC-SHA256
olarak imzalanıyor. İmza, dosya sırasından bağımsız olacak şekilde sıralanmış
satırlar üzerinden hesaplanıyor:

```python
def sign_baseline(target_path, follow_symlinks, entries) -> str:
    mac = hmac.new(get_hmac_key(), digestmod=hashlib.sha256)
    mac.update(json.dumps([target_path, bool(follow_symlinks)]).encode() + b"\n")
    rows = sorted(
        [_get(e, k) for k in ("file_path", "sha256", "size_bytes", "mode", "uid", "gid")]
        for e in entries
    )
    for row in rows:
        mac.update(json.dumps(row, separators=(",", ":")).encode() + b"\n")
    return mac.hexdigest()
```

İmzası tutmayan bir temel kayıtla tarama yapılmak istendiğinde istek HTTP 409
ile reddediliyor ve girişim denetim kaydına yazılıyor.

**Denetim kaydı zincirleniyor.** Yapılan her işlem bir denetim kaydına
yazılıyor ve her satır bir önceki satırın özetine bağlanıyor. Bir satırın
silinmesi, değiştirilmesi ya da sırasının bozulması zinciri kırıyor;
`verify-audit` komutu kırılan satırı gösteriyor. PostgreSQL üzerinde ayrıca
bir tetikleyici bu tablodaki UPDATE ve DELETE işlemlerini engelliyor.

**Sembolik bağlantılar takip edilmiyor.** Bağlantının hedefi kaydediliyor.
Böylece bir bağlantının başka bir dosyaya yönlendirilmesi değişiklik olarak
görülüyor ve izlenen klasörün dışındaki dosyalar okunmuyor.

**Okunamayan dosya silinmiş sayılmıyor.** İzin nedeniyle okunamayan bir dosya
`DELETED` olarak değil, hata olarak raporlanıyor. Adli bir incelemede bu ayrım
yanlış sonuca varılmasını önlüyor.

`FIM_HMAC_KEY` değerinin izlenen sunucunun veritabanından ayrı bir yerde
saklanması gerekiyor. Hem veritabanına hem anahtara erişen bir saldırgan
temel kaydı yeniden imzalayabilir; bu, aracın belgelenmiş sınırı.

## Günlük kullanım

`scan` komutu değişiklik bulduğunda 2 çıkış koduyla sonlanıyor. Bu sayede araç
doğrudan zamanlanmış görevlere bağlanabiliyor:

```bash
0 * * * * fim-sentinel scan -b 1 || echo "Bütünlük uyarısı" | mail -s FIM yonetici@ornek.com
```

Aynı işlemler REST API üzerinden de yapılabiliyor. API, `X-API-Key` başlığı
istiyor ve yalnızca `FIM_ALLOWED_PATHS` ile izin verilen klasörleri
tarayabiliyor. Komut satırı ve API aynı servis katmanını kullandığı için
kurallar iki ayrı yerde yazılmıyor.
