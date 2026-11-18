---
title: "Brute-Force Tespiti: Şifresini Unutan Kullanıcıyı Bottan Ayırmak"
kisa: SSH ve web auth log'larından brute-force saldırılarını tespit eden, her alarmı gerekçesiyle veren bir analiz servisi.
ozet: "Her başarısız login'e alarm üreten bir sistem, kısa süre içinde kimsenin bakmadığı bir sisteme dönüşür. Brute-force tespitinde asıl iş saldırıyı bulmak değil, false positive'leri ayıklamaktır."
date: 2026-09-18
teknolojiler: [Python, FastAPI, SQLAlchemy, PostgreSQL, pytest, Docker]
repo: https://github.com/hasancrlk/kaba-kuvvet-saldiri-tespiti
kategori: guvenlik
sira: 1
ref: authwatch
---

İnternete açık bir SSH sunucusunun `auth.log` dosyasına bakarsanız şöyle
satırlar görürsünüz:

```
Sep 17 03:12:01 srv01 sshd[4101]: Failed password for invalid user admin from 203.0.113.5
Sep 17 03:12:04 srv01 sshd[4102]: Failed password for invalid user oracle from 203.0.113.5
Sep 17 03:12:07 srv01 sshd[4103]: Failed password for root from 203.0.113.5
Sep 17 03:12:10 srv01 sshd[4104]: Failed password for invalid user postgres from 203.0.113.5
```

Aynı IP, üç saniye arayla, her seferinde farklı bir username. Bu açıkça bir bot.
Aynı log dosyasında şunlar da var:

```
Sep 17 09:42:10 srv01 sshd[5210]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:16 srv01 sshd[5211]: Failed password for deniz from 198.51.100.7
Sep 17 09:42:41 srv01 sshd[5212]: Failed password for deniz from 198.51.100.7
```

Bu ise büyük ihtimalle şifresini hatırlamaya çalışan bir çalışan. İkisi de aynı
kuralı tetikler, ama biri saldırı diğeri değil. Bu yazıda EMT Cyber stajında
ödev olarak geliştirdiğim AuthWatch'ı ve bu ayrımı nasıl yaptığını anlatıyorum.

*Örnekler depodaki sample log dosyasından alındı; IP adresleri dokümantasyon
için ayrılmış aralıklardan.*

## Fixed window değil, sliding window

Temel kural basit: aynı IP'den 60 saniye içinde 5 başarısız deneme varsa alarm.
Ancak sayaç her dakika sıfırlanırsa (fixed window), saldırgan bir pencerenin
sonunda 4, sonrakinin başında 4 deneme yaparak threshold'un altında kalabilir.

Bu yüzden **sliding window** kullandım. Her IP için bir `deque` tutuluyor ve
yeni bir deneme geldiğinde pencerenin dışına düşen kayıtlar atılıyor:

```python
bucket.append(event)
while bucket and event.timestamp - bucket[0].timestamp > window:
    bucket.popleft()
if len(bucket) >= threshold:
    alarm_uret()
```

Her event kuyruğa bir kez girip bir kez çıktığı için maliyet O(n); büyük bir log
tek geçişte işleniyor. Fixed window'un kaçırdığı 4+4 dizisi depoda ayrı bir test
olarak duruyor.

Ayrıca bir **cooldown** süresi var. Threshold aşıldıktan sonra her yeni deneme
için alarm üretilseydi, 500 denemelik bir saldırı 496 alarm demekti. Aynı IP için
varsayılan olarak 300 saniye boyunca yeni alarm üretilmiyor.

## Confidence score: kullanıcı mı, bot mu?

Threshold'u geçen her burst'ü saldırı saymak yerine her alarma bir confidence
score veriyorum. Skor denemelerin biçimine bakıyor:

- **Username çeşitliliği.** Üç ve üzeri farklı username denenmişse skor artıyor;
  tek bir username ise düşüyor.
- **Var olmayan kullanıcılar.** `invalid user` satırları user enumeration
  işareti.
- **Zamanlama düzenliliği.** Denemeler arası sürelerin varyasyon katsayısına
  bakılıyor. İnsan düzensiz aralıklarla dener, otomasyon sabit aralıklarla.
- **Yoğunluk.** Threshold'un üç katı ve üzeri deneme skoru artırıyor.
- **Geçmiş.** Aynı IP'den daha önce başarılı login varsa skor düşüyor.

Sonuç `high`, `medium` veya `low` olarak etiketleniyor ve her alarm bu kararın
gerekçesini taşıyor:

```
203.0.113.5   confidence: high (0.95)
  - 5 farkli kullanici adi denendi (kullanici tarama).
  - 4 deneme var olmayan kullanici adina yapildi.
  - Denemeler neredeyse sabit araliklarla geldi (otomasyon izi).

198.51.100.7  confidence: low (0.0)
  - Tek kullanici adi - parolasini unutmus bir kullanici olabilir.
  - Bu IP daha once basariyla giris yapmis (bilinen kaynak).
```

Low confidence alarmlar silinmiyor, yalnızca etiketleniyor. Kendi kendini
filtreleyen bir sistem gerçek bir saldırıyı da sessizce yutabilir; karar
analistte kalmalı.

Bir ayrıntı: web access log'larında username alanı çoğunlukla `-` gelir. Bu
durumda "tek username" indirimi uygulanmıyor; sinyal yoksa indirim de yok.

## Account takeover tespiti

Bir IP aynı username'e art arda başarısız denemeler yapıp ardından o hesapla
başarılı login olursa ayrı bir alarm üretiliyor: `possible_account_takeover`.
Username eşleşmesi zorunlu. `admin` hesabına yapılan saldırıdan sonra `deploy`
ile yapılan normal bir login bu kapsama girmiyor.

## Desteklenen log formatları

SSH `auth.log`, nginx/apache combined log ve JSON satırları. Parse edilemeyen
satırlar atılmıyor; sayılıyor ve örnekleri saklanıyor. `auth.log` timestamp'inde
yıl bilgisi olmadığı için yıl, upload sırasında parametre olarak veriliyor.

## Kapanış

AuthWatch'ın bilinen sınırları var. Tespit IP bazlı olduğu için her IP'den az
sayıda deneme yapan dağıtık bir botnet threshold'a takılmıyor; bunun için
kullanıcı ya da ASN bazlı bir boyut gerekir. Her upload ayrı işlendiği için iki
dosyaya bölünmüş bir saldırı ikiye ayrılabiliyor. `X-Forwarded-For` okunmuyor ve
servisin kendisinde authentication yok.

Brute-force tespitinde asıl değer yakalanan saldırı sayısında değil, analistin
güvenebildiği alarm sayısındadır. Gerekçesini söyleyen bir alarm, sadece "ALARM"
diyen bir satırdan çok daha kullanışlıdır.

Proje 48 testle geliyor; sample log depoda olduğu için `docker compose up`
sonrası hemen denenebilir.
