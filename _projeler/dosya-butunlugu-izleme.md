---
title: "File Integrity Monitoring: Baseline'ın Kendisi Değiştirilirse Ne Olur?"
kisa: Bir klasörün imzalı baseline'ını alıp sonradan değişen, eklenen ve silinen dosyaları tespit eden bir FIM aracı.
ozet: "Bir FIM aracı dosyalardaki değişikliği yakalayabilir; ama saldırgan aracın kendi kayıtlarını da değiştirirse bunu fark edebilir mi? Chain of custody tam olarak bu soruyla ilgili."
date: 2026-09-17
teknolojiler: [Python, FastAPI, SQLAlchemy, Alembic, Typer, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/dosya-butunlugu-izleme
kategori: guvenlik
sira: 2
ref: fim-sentinel
---

Bir sunucuya sızan saldırgan çoğu zaman dosya sisteminde iz bırakır: bir sayfaya
zararlı kod ekler, `shell.php` gibi bir web shell yükler ya da bir config
dosyasını değiştirir. File Integrity Monitoring (FIM) bu değişiklikleri yakalamak
için kullanılan klasik yöntem.

Staja başlamadan önce FIM kavramını bilmiyordum; EMT Cyber'de ödev olarak
önüme geldiğinde ilk iş ne olduğunu ve neden bu kadar yaygın kullanıldığını
anlamak oldu. Bu yazıda geliştirdiğim FIM-Sentinel'i ve özellikle aracın kendi
kayıtlarını nasıl koruduğunu anlatıyorum.

## FIM nasıl çalışır?

İki adımdan oluşur:

1. Klasörün güvenilir hâlinin bir **baseline**'ı alınır: her dosyanın hash'i,
   boyutu, izinleri ve sahibi.
2. Klasör belirli aralıklarla yeniden taranır ve baseline ile karşılaştırılır.

```
$ python -m cli.fim_cli baseline --path /var/www/html
$ python -m cli.fim_cli scan --baseline-id 1

│ MODIFIED │ /var/www/html/index.html │ Hash mismatch detected. │
│ MODIFIED │ /var/www/html/config.php │ Hash mismatch detected. │
│ ADDED    │ /var/www/html/shell.php  │ New file detected.      │
```

Dosyalar 64 KB'lık chunk'lar hâlinde okunup SHA-256 ile hash'leniyor; büyük
dosyalar belleği zorlamıyor.

## Asıl problem: baseline'ın bütünlüğü

Karşılaştırma ne kadar doğru olursa olsun baseline bir veritabanında duruyor.
Veritabanına erişen bir saldırgan, yüklediği `shell.php`'yi baseline'a da ekler
ve tarama "değişiklik yok" der.

Adli bilişimde bu soru **chain of custody** (delil zinciri) kavramıyla karşılanır:
delilin toplandığı andan itibaren değiştirilmediğini kanıtlayabilmek. FIM-Sentinel
bunun için şu önlemleri alıyor:

**Baseline imzalanıyor.** Her baseline `FIM_HMAC_KEY` ile HMAC-SHA256 olarak
imzalanıyor. İmza, dosya sırasından bağımsız olsun diye sıralanmış satırlar
üzerinden hesaplanıyor:

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

İmzası tutmayan bir baseline ile tarama istenirse API HTTP 409 dönüyor ve bu
girişim audit log'a yazılıyor.

**Audit log zincirleniyor.** Her işlem bir audit log'a yazılıyor ve her satır bir
öncekinin hash'ine bağlı (tamper-evident log). Bir satırı silmek, değiştirmek ya
da sırasını bozmak zinciri kırıyor; `verify-audit` komutu kırılan satırı
gösteriyor. PostgreSQL tarafında bir trigger bu tablodaki UPDATE ve DELETE
işlemlerini ayrıca engelliyor.

**Symlink'ler takip edilmiyor.** Link'in hedefi kaydediliyor. Böylece bir
symlink'in başka bir dosyaya yönlendirilmesi değişiklik olarak yakalanıyor ve
izlenen klasörün dışındaki dosyalar okunmuyor.

**Okunamayan dosya "silindi" sayılmıyor.** Permission nedeniyle okunamayan bir
dosya `DELETED` olarak değil, error olarak raporlanıyor. Bir incelemede bu ayrım
yanlış bir sonuca varılmasını önlüyor.

Bunun belgelenmiş bir sınırı var: `FIM_HMAC_KEY` izlenen sunucunun
veritabanından ayrı bir yerde (örneğin bir secret manager'da) tutulmalı. Hem
veritabanına hem key'e erişen biri baseline'ı yeniden imzalayabilir.

## Otomasyon ve API

`scan` komutu değişiklik bulduğunda exit code 2 ile bitiyor; bu sayede araç
doğrudan cron'a ya da bir CI job'ına bağlanabiliyor:

```bash
0 * * * * fim-sentinel scan -b 1 || echo "FIM alert" | mail -s FIM admin@example.com
```

Aynı işlemler REST API üzerinden de yapılabiliyor. API `X-API-Key` istiyor ve
yalnızca `FIM_ALLOWED_PATHS` ile izin verilen dizinleri tarayabiliyor. CLI ve API
aynı service katmanını kullandığı için hiçbir kural iki kez yazılmadı.

## Kapanış

Değişikliği tespit eden bir araç yazmak görece kolay. Asıl zor olan, aracın kendi
kayıtlarının değiştirilmediğini kanıtlayabilmesi. Bir güvenlik aracını tasarlarken
"saldırgan bu aracın kendisine ne yapar?" sorusunu sormak; imzalı baseline,
zincirli audit log ve veritabanı trigger'ı gibi önlemleri doğal olarak gündeme
getiriyor.
