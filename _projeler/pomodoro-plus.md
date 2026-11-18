---
title: "Kendim için geliştirdiğim odak uygulaması: Pomodoro Plus"
kisa: Telefonu elden bırakmayı puanla ödüllendiren, mobil öncelikli (PWA) pomodoro uygulaması. Geliştirme sürüyor.
ozet: "Bir pomodoro sayacı süreyi sayar ama telefonun elinizde olup olmadığıyla ilgilenmez. Peki sayaç telefonu bırakmanızı ödüllendirse?"
date: 2026-08-11
teknolojiler: [Next.js, TypeScript, Tailwind CSS, Zustand, PWA]
repo: https://github.com/hasancrlk/Pomodoro_Plus
kategori: mobil-web
sira: 8
ref: pomodoro
---

> **Durum:** Uygulama hâlâ geliştirme aşamasında. Tamamlayınca App Store ve
> Google Play'de yayınlamayı planlıyorum. Bu yazı şu anki sürümü anlatıyor.

Pomodoro tekniği basit: 25 dakika odaklan, 5 dakika mola ver. Pomodoro
Plus'ı kendim için yazmaya başladım. Fikir şu: odak süresini telefona
dokunmadan tamamlarsanız daha fazla puan kazanıyorsunuz.

## Puanlar

- Odak süresini telefona dokunmadan bitirirseniz **+12**.
- Bitirirseniz ama arada telefona dokunduysanız **+6**.
- Molayı tamamlarsanız **+2**.
- Sayacı iptal ederseniz **−5**.

İptal cezasını bilerek ödüllerden küçük tuttum. Amacım uygulamayı açmaktan
kaçındırmak değil, süreyi tamamlamaya teşvik etmek. Kazandığınız puanlarla
mağazadan Altın, Neon, Orman ve Okyanus temalarını, ek mola hakkını ve
rozetleri açabiliyorsunuz.

## Telefona dokunduğunuzu nasıl anlıyor?

Bir web uygulaması telefonun genel kullanımını göremez. Elimdeki en yakın
sinyal, uygulama sayfasının arka plana geçip geçmediği. Başka bir uygulamaya
geçtiğinizde tarayıcı `visibilitychange` olayını tetikliyor:

```tsx
useEffect(() => {
  function onVisibilityChange() {
    if (document.hidden) markDistracted();
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return () => document.removeEventListener("visibilitychange", onVisibilityChange);
}, [markDistracted]);
```

Bunun yaklaşık bir ölçüm olduğunu baştan söyleyeyim: ekranı kapatmanız da
sayfayı gizliyor ve aynı olayı tetikliyor. Gerçek bir ekran süresi ölçümü
için cihazın kendi (native) API'lerine erişmek gerekiyor; bu, mağaza sürümünün
yapılacaklar listesinde.

## Acil durumlar için bir kapı

Odak süresi boyunca uygulamanın diğer bölümleri kilitleniyor. Tek istisna
önceden eklediğiniz acil kişiler; onları `tel:` bağlantısıyla
arayabiliyorsunuz.

## Nasıl yaptım?

Arayüzü Next.js App Router, TypeScript ve Tailwind CSS v4 ile yazdım; sayaç
dairesel bir geri sayım animasyonuyla dönüyor. Durumu Zustand ile
yönetiyorum. Puanlar, puan geçmişi, acil kişiler, satın aldıklarınız ve
seçtiğiniz tema tarayıcıda saklanıyor; sunucu ya da hesap gerekmiyor. Bir web
manifesti ve service worker sayesinde uygulamayı ana ekrana ekleyebiliyor,
internet yokken de temel olarak kullanabiliyorsunuz.

## Sırada ne var?

- Sayaç şu an kalan süreyi her saniye bir azaltıyor. Tarayıcılar arka
  plandaki sekmelerde zamanlayıcıları yavaşlattığı için süre kayabiliyor.
  Bitiş anını saklayıp kalan süreyi ondan hesaplamak daha doğru olacak.
- Süre dolduğunda bildirim.
- Puan geçmişi zaten tutuluyor; onu gösteren bir istatistik ekranı.
- Mağaza sürümü için native ekran süresi entegrasyonu.
