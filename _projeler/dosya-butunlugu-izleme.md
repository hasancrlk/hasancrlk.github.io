---
title: "Saldırgan izini silmeye çalışırsa: imzalı dosya bütünlüğü izleme"
kisa: Bir klasörün imzalı parmak izini alıp sonradan değişen, eklenen ve silinen dosyaları bulan adli bilişim aracı.
ozet: "Bir klasörün parmak izini alıp sonradan değişen dosyaları bulan bir araç yazdım. Asıl soru şuydu: saldırgan parmak izinin kendisini de değiştirirse ne olur?"
date: 2026-09-17
teknolojiler: [Python, FastAPI, SQLAlchemy, Alembic, Typer, PostgreSQL, Docker]
repo: https://github.com/hasancrlk/dosya-butunlugu-izleme
kategori: guvenlik
sira: 2
ref: fim-sentinel
---

## Problem

Bir web sunucusuna sızan saldırgan genellikle iz bırakır. Ana sayfaya zararlı
bir script ekler, klasöre `shell.php` adında bir arka kapı bırakır ya da bir
yapılandırma dosyasını değiştirir. Bu değişiklikler haftalarca fark
edilmeyebilir.

**Dosya bütünlüğü izleme** (File Integrity Monitoring, FIM) buna karşı eski ve
etkili bir yöntem. Önce klasörün "temiz" hâlinin parmak izi alınır, buna temel
kayıt (baseline) denir. Sonra düzenli aralıklarla yeniden taranıp
karşılaştırılır:

```
$ python -m cli.fim_cli scan --baseline-id 1
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Type     ┃ File Path                ┃ Detail                  ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ MODIFIED │ /var/www/html/index.html │ Hash mismatch detected. │
│ MODIFIED │ /var/www/html/config.php │ Hash mismatch detected. │
│ ADDED    │ /var/www/html/shell.php  │ New file detected.      │
└──────────┴──────────────────────────┴─────────────────────────┘
```

Buraya kadarı kolay. Zor kısım şu soru: **saldırgan temel kaydı da
değiştirirse?** Veritabanına erişebilen biri `shell.php` dosyasını temel
kayda ekler ve araç "her şey yolunda" der.

## Zor kısım: Delil zinciri

Adli bilişimde buna **delil zinciri** (chain of custody) denir: delilin
sonradan kurcalanmadığını kanıtlayabilmek. Bunun için beş katman kurdum.

**1. Temel kayıt imzalı.** Her temel kayıt gizli bir anahtarla (HMAC-SHA256)
imzalanıyor. İmza dosya sırasından bağımsız, kanonik bir biçim üzerinden
hesaplanıyor:

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

Veritabanında elle değiştirilmiş bir temel kayıt tarama anında reddediliyor
(HTTP 409) ve bu girişim de kayda geçiyor.

**2. Denetim kaydı zincirli.** Yapılan her işlem bir denetim kaydına yazılıyor
ve her satır bir öncekinin özetine bağlı. Ortadan bir satır silmek, bir satırı
değiştirmek ya da sırayı bozmak zinciri kırıyor. `verify-audit` komutu
zinciri baştan sona doğrulayıp kırık satırı gösteriyor. PostgreSQL'de ayrıca
bir tetikleyici UPDATE ve DELETE işlemlerini engelliyor.

**3. Yalnızca içerik değil, izinler de izleniyor.** SHA-256 özetinin yanında
boyut, dosya izinleri ve sahibi de kaydediliyor. Bir dosyanın içeriği aynı
kalıp herkese yazılabilir hâle getirilmesi de bir bulgu.

**4. Sembolik bağlantılar takip edilmiyor.** Bağlantının hedefi kaydediliyor.
Böylece bir bağlantının başka yere yönlendirilmesi yakalanıyor ve izlenen
klasörün dışındaki hiçbir dosya okunmuyor:

```python
if stat.S_ISLNK(st.st_mode) and not follow_symlinks:
    target = os.readlink(file_path)
    result.sha256 = hashlib.sha256(f"symlink:{target}".encode()).hexdigest()
```

**5. Okunamayan dosya "silindi" sayılmıyor.** Bir dosya var ama izin
yüzünden okunamıyorsa hata olarak raporlanıyor. Bunu `DELETED` diye
raporlamak, araştırmacıyı yanlış bir hikâyenin peşine düşürürdü.

> Anahtarın nerede durduğu kritik: hem veritabanını hem `FIM_HMAC_KEY`
> anahtarını ele geçiren biri temel kaydı sahteleyebilir. Anahtar izlenen
> sunucunun dışında, bir sır yöneticisinde durmalı.

## Büyük dosyalar

Dosyalar 64 KB'lık parçalar hâlinde okunup özetleniyor. Gigabaytlık bir
dosya belleği şişirmiyor. Taramada bir izin hatası ya da bağlantı döngüsü
çıkarsa kaydediliyor, araç çökmüyor.

## Otomasyona bağlamak

`scan` komutu değişiklik bulunca **2** koduyla çıkıyor. Bu küçük ayrıntı aracı
cron ya da CI işine bağlamayı kolaylaştırıyor:

```bash
0 * * * * fim-sentinel scan -b 1 || echo "Bütünlük uyarısı" | mail -s FIM yonetici@ornek.com
```

## Öğrendiklerim

Bir güvenlik aracını tasarlarken "saldırgan bu aracın kendisine ne yapar?"
diye sormayı öğrendim. Değişikliği bulan bir araç yazmak kolay. Kendi
kayıtlarının değiştirilmediğini kanıtlayabilen bir araç yazmak asıl iş. Bu
soru beni imzalara, zincirli kayda ve veritabanı tetikleyicisine götürdü.
Komut satırı ve REST API aynı servis katmanını kullanıyor, böylece bir kural
iki yerde ayrı ayrı yazılmıyor.
