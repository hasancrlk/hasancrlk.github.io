---
title: "Telefona dokunmadan çalış, puan kazan: Pomodoro Plus"
kisa: Telefonu elden bırakmayı puanla ödüllendiren, mobil öncelikli (PWA) pomodoro uygulaması.
ozet: "Telefonu elinden bırakamayanlar için bir pomodoro uygulaması yaptım. Odak süresini telefona dokunmadan tamamlayan daha çok puan kazanıyor, puanlarla yeni temalar açılıyor."
date: 2026-08-11
teknolojiler: [Next.js, TypeScript, Tailwind CSS, Zustand, PWA]
repo: https://github.com/hasancrlk/Pomodoro_Plus
kategori: mobil-web
sira: 8
ref: pomodoro
---

## Fikir

Pomodoro tekniği basit: 25 dakika odaklan, 5 dakika mola ver. Sorun şu ki
asıl dikkat dağıtıcı genellikle sayacın çalıştığı cihazın kendisi. Sayacı
başlatıp üç dakika sonra sosyal medyaya bakan biri için klasik bir sayaç
hiçbir şey değiştirmiyor.

Pomodoro Plus'ın fikri telefonu elden bırakmayı **ödüllendirmek**:

| Olay | Emek puanı |
|---|---:|
| Odak süresi telefona dokunmadan tamamlandı | +12 |
| Odak süresi tamamlandı ama telefona dokunuldu | +6 |
| Mola tamamlandı | +2 |
| Sayaç iptal edildi | −5 |

Kazanılan puanlarla mağazadan yeni temalar (Altın, Neon, Orman, Okyanus),
ekstra mola hakkı ve rozetler açılıyor.

## "Telefona dokunuldu mu?" nasıl anlaşılıyor?

Bir web uygulaması telefonun genel kullanımını göremez. Yapabildiğim en iyi
yaklaşım, sayfanın arka plana geçip geçmediğini izlemek. Kullanıcı başka bir
uygulamaya geçerse tarayıcı `visibilitychange` olayı gönderiyor:

```tsx
useEffect(() => {
  function onVisibilityChange() {
    if (document.hidden) markDistracted();
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return () => document.removeEventListener("visibilitychange", onVisibilityChange);
}, [markDistracted]);
```

Bu ölçüm **yaklaşık**: ekranı kapatıp telefonu masaya bırakmak da sayfayı
gizler. Bunu README'de açıkça yazdım. Gerçek bir "ekran süresi" ölçümü native
API ister, yani uygulamanın React Native gibi bir yapıya taşınması gerekir.

## Acil kişiler

Odak sırasında diğer sekmeler kilitleniyor. Tek istisna kullanıcının önceden
eklediği **acil kişiler**: onlar `tel:` bağlantısıyla aranabiliyor. Odaklanmak
önemli ama annenizi arayamayacağınız kadar değil.

## Teknik tarafı

- **Durum yönetimi:** Zustand. Puanlar, puan geçmişi, acil kişiler, satın
  alınanlar ve aktif tema `persist` ile tarayıcıda saklanıyor. Sunucu yok,
  hesap yok.
- **PWA:** `manifest.webmanifest` ve küçük bir service worker sayesinde ana
  ekrana eklenebiliyor ve temel çevrimdışı önbellekleme yapıyor.
- **Arayüz:** Next.js App Router, Tailwind CSS v4, dairesel geri sayım
  animasyonu.

## Bir dahaki sefere farklı yapacaklarım

Sayaç şu an her saniye kalan süreyi bir azaltıyor. Tarayıcılar arka plandaki
sekmelerde zamanlayıcıları yavaşlattığı için bu süre kayabilir. Daha doğru
yol, bitiş anını saklayıp kalan süreyi her seferinde ondan hesaplamak. Ayrıca
sayaç bittiğinde bildirim ve istatistik ekranı eksik. Puan geçmişi zaten
tutuluyor, yalnızca bir görünüm gerekiyor.

## Öğrendiklerim

Web platformunun sınırlarını tanımayı öğrendim. Bir özelliği "yaklaşık"
yapmak sorun değil, yeter ki kullanıcıya dürüstçe söylensin. Oyunlaştırmada
da cezanın ödülden küçük tutulması gerektiğini gördüm. İptal cezası büyük
olsaydı insanlar uygulamayı açmaktan kaçınırdı.
