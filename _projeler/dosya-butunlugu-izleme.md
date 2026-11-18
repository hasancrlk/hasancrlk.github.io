---
title: "Staja başlarken adını bilmediğim bir araç: dosya bütünlüğü izleme"
kisa: Bir klasörün imzalı parmak izini alıp sonradan değişen, eklenen ve silinen dosyaları bulan adli bilişim aracı.
ozet: "Staja başladığımda \"File Integrity Monitoring\" diye bir şey duymamıştım. Ödev olarak önüme geldiğinde ilk sorum basitti: bir dosyanın değiştiğini nasıl anlarsınız? Asıl soru ise daha sonra geldi."
date: 2026-09-17
teknolojiler: [Python, FastAPI, SQLAlchemy, Alembic, Typer, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/dosya-butunlugu-izleme
kategori: guvenlik
sira: 2
ref: fim-sentinel
---

Bir sunucuya sızan saldırgan dosya sisteminde iz bırakır: bir sayfaya zararlı
kod ekler, `shell.php` gibi bir arka kapı yükler ya da bir yapılandırma
dosyasını değiştirir. Dosya bütünlüğü izleme (FIM) bunları yakalamak için iki
adım kullanıyor:

1. Klasörün güvenilir hâlinin parmak izini alıyorsunuz. Buna **temel kayıt**
   (baseline) deniyor.
2. Klasörü belirli aralıklarla yeniden tarayıp temel kayıtla
   karşılaştırıyorsunuz.

Yazdığım aracın komut satırında bu şöyle görünüyor:

```
$ python -m cli.fim_cli baseline --path /var/www/html
$ python -m cli.fim_cli scan --baseline-id 1

│ MODIFIED │ /var/www/html/index.html │ Hash mismatch detected. │
│ MODIFIED │ /var/www/html/config.php │ Hash mismatch detected. │
│ ADDED    │ /var/www/html/shell.php  │ New file detected.      │
```

Her dosya için SHA-256 özetini, boyutunu, izinlerini ve sahibini
saklıyorum. Dosyaları 64 KB'lık parçalar hâlinde okuduğum için büyük dosyalar
belleği zorlamıyor.

## Peki saldırgan temel kaydı da değiştirirse?

Karşılaştırma ne kadar iyi olursa olsun, temel kayıt sonuçta bir
veritabanında duruyor. Veritabanına erişen bir saldırgan yüklediği
`shell.php`'yi temel kayda da ekler ve tarama "her şey yolunda" der.

Adli bilişimde buna **delil zinciri** (chain of custody) deniyor: delilin
toplandığı andan itibaren değiştirilmediğini kanıtlayabilmek. Araçta bunun
için birkaç önlem aldım.

**Temel kaydı imzalıyorum.** Her temel kayıt `FIM_HMAC_KEY` ile HMAC-SHA256
olarak imzalanıyor. İmzayı dosya sırasından bağımsız olsun diye sıralanmış
satırlar üzerinden hesaplıyorum:

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

İmzası tutmayan bir temel kayıtla tarama istenirse araç HTTP 409 ile
reddediyor ve bu girişimi de kayda geçiriyor.

**Denetim kaydını zincirliyorum.** Yapılan her işlem bir denetim kaydına
yazılıyor ve her satır bir öncekinin özetine bağlı. Ortadan bir satır silmek,
bir satırı değiştirmek ya da sırayı bozmak zinciri kırıyor; `verify-audit`
komutu kırılan yeri gösteriyor. PostgreSQL'de ayrıca bir tetikleyici bu
tablodaki UPDATE ve DELETE işlemlerini engelliyor.

**Sembolik bağlantıları takip etmiyorum.** Bağlantının hedefini
kaydediyorum. Böylece bağlantının başka bir dosyaya çevrilmesi değişiklik
olarak görünüyor ve izlenen klasörün dışına hiç çıkılmıyor.

**Okunamayan dosyayı silinmiş saymıyorum.** İzin yüzünden okunamayan bir
dosya `DELETED` değil, hata olarak raporlanıyor. Adli bir incelemede bu ayrım
yanlış bir sonuca varmanızı önlüyor.

Bunun bir sınırı var ve açıkça yazmak istiyorum: `FIM_HMAC_KEY` izlenen
sunucunun veritabanından ayrı bir yerde durmalı. Hem veritabanına hem
anahtara erişen biri temel kaydı yeniden imzalayabilir.

## Günlük kullanım

`scan` komutu değişiklik bulduğunda 2 çıkış koduyla bitiyor. Bu küçük ayrıntı
sayesinde aracı doğrudan zamanlanmış bir göreve bağlayabiliyorsunuz:

```bash
0 * * * * fim-sentinel scan -b 1 || echo "Bütünlük uyarısı" | mail -s FIM yonetici@ornek.com
```

Aynı işlemleri REST API üzerinden de yapabiliyorsunuz. API `X-API-Key`
istiyor ve yalnızca `FIM_ALLOWED_PATHS` ile izin verilen klasörleri
tarayabiliyor. Komut satırı ile API aynı servis katmanını kullandığı için
hiçbir kuralı iki kez yazmadım.
