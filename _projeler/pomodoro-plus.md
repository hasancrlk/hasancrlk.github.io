---
title: "Kendim için geliştirdiğim odak uygulaması: Pomodoro Plus"
kisa: Telefonu elden bırakmayı puanla ödüllendiren, mobil öncelikli (PWA) pomodoro uygulaması. Geliştirme sürüyor.
ozet: "Pomodoro Plus'ı kendi çalışma düzenim için geliştiriyorum. Odak süresini telefona dokunmadan tamamlayan kullanıcı daha fazla puan kazanıyor. Uygulama henüz geliştirme aşamasında; hedef App Store ve Google Play."
date: 2026-08-11
teknolojiler: [Next.js, TypeScript, Tailwind CSS, Zustand, PWA]
repo: https://github.com/hasancrlk/Pomodoro_Plus
kategori: mobil-web
sira: 8
ref: pomodoro
---

> **Durum:** Uygulama geliştirme aşamasında. Tamamlandığında App Store ve
> Google Play'de yayınlamayı planlıyorum. Bu yazı mevcut sürümü anlatıyor.

Pomodoro tekniği 25 dakika odaklanma ve 5 dakika moladan oluşur. Bu
uygulamayı kendi çalışma düzenim için yazmaya başladım. Klasik bir zamanlayıcı
sürenin ne kadar kaldığını gösterir ama sayaç çalışırken telefonun elde olup
olmadığıyla ilgilenmez. Pomodoro Plus'ın temel fikri, telefonu bırakmayı bir
puan sistemiyle teşvik etmek.

## Puan sistemi

- Odak süresi telefona dokunulmadan tamamlanırsa **+12** puan.
- Odak süresi tamamlanır ama arada telefona dokunulursa **+6** puan.
- Mola tamamlanırsa **+2** puan.
- Sayaç iptal edilirse **−5** puan.

İptal cezası ödüllerden küçük tutuldu; amaç uygulamayı açmayı caydırmak
değil, süreyi tamamlamayı teşvik etmek. Kazanılan puanlarla mağazadan Altın,
Neon, Orman ve Okyanus temaları, ek mola hakkı ve rozetler açılıyor.

## Telefona dokunulduğunun tespiti

Bir web uygulaması cihazın genel kullanımına erişemez. Kullanılabilecek en
yakın sinyal, uygulama sayfasının arka plana geçip geçmediği. Kullanıcı
başka bir uygulamaya geçtiğinde tarayıcı `visibilitychange` olayını
tetikliyor:

```tsx
useEffect(() => {
  function onVisibilityChange() {
    if (document.hidden) markDistracted();
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return () => document.removeEventListener("visibilitychange", onVisibilityChange);
}, [markDistracted]);
```

Bu ölçüm yaklaşık bir ölçüm. Ekranın kapatılması da sayfayı gizler ve aynı
olayı tetikler. Kesin bir ekran süresi ölçümü için cihazın yerel (native)
API'lerine erişim gerekiyor; mağaza sürümü için bu konu yol haritasında.

## Acil kişiler

Odak süresi boyunca uygulamanın diğer bölümleri kilitleniyor. Tek istisna
kullanıcının önceden eklediği acil kişiler; bu kişiler `tel:` bağlantısıyla
aranabiliyor.

## Teknik yapı

- **Arayüz:** Next.js App Router, TypeScript ve Tailwind CSS v4. Sayaç
  dairesel bir geri sayım animasyonuyla gösteriliyor.
- **Durum yönetimi:** Zustand. Puanlar, puan geçmişi, acil kişiler, satın
  alınan öğeler ve etkin tema `persist` ile tarayıcıda saklanıyor. Sunucu ya
  da hesap gerekmiyor.
- **PWA:** Web manifesti ve bir service worker ile uygulama ana ekrana
  eklenebiliyor ve temel çevrimdışı önbellekleme yapıyor.

## Sıradaki adımlar

- Sayaç şu anda kalan süreyi her saniye bir azaltıyor. Tarayıcılar arka
  plandaki sekmelerde zamanlayıcıları yavaşlattığı için süre kayabiliyor.
  Bitiş anını saklayıp kalan süreyi ondan hesaplamak daha doğru bir yöntem.
- Süre dolduğunda bildirim gönderilmesi.
- Puan geçmişi zaten tutuluyor; bunu gösteren bir istatistik ekranı.
- Mağaza sürümü için native ekran süresi entegrasyonu.
