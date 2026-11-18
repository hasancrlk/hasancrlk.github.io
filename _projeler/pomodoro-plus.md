---
title: "Pomodoro Plus: Telefonu Bırakmayı Ödüllendiren Bir Odak Uygulaması"
kisa: Odak süresini telefona dokunmadan tamamlayanı puanla ödüllendiren, mobile-first bir PWA. Geliştirme sürüyor.
ozet: "Klasik bir pomodoro timer'ı süreyi sayar, ama timer çalışırken telefonun elinizde olup olmadığıyla ilgilenmez. Pomodoro Plus'ın fikri, telefonu bırakmayı bir puan sistemiyle teşvik etmek."
date: 2026-08-11
teknolojiler: [Next.js, TypeScript, Tailwind CSS, Zustand, PWA]
repo: https://github.com/hasancrlk/Pomodoro_Plus
kategori: mobil-web
sira: 8
ref: pomodoro
---

> **Durum:** Uygulama geliştirme aşamasında. Tamamlandığında App Store ve Google
> Play'de yayınlamayı planlıyorum. Bu yazı mevcut sürümü anlatıyor.

Pomodoro tekniği 25 dakika odaklanma ve 5 dakika moladan oluşur. Pomodoro Plus'ı
kendi kullanımım için geliştirmeye başladım. Bu yazıda uygulamanın puan
sistemini, "telefona dokunuldu mu?" sorusunu bir web uygulamasında nasıl
yaklaşık olarak cevapladığımı ve teknik yapıyı anlatıyorum.

## Puan sistemi

- **Telefona dokunmadan tamamlanan odak süresi:** +12 puan.
- **Tamamlanan ama arada telefona dokunulan odak süresi:** +6 puan.
- **Tamamlanan mola:** +2 puan.
- **İptal edilen timer:** −5 puan.

İptal cezası bilinçli olarak ödüllerden küçük tutuldu; amaç uygulamayı açmayı
caydırmak değil, süreyi tamamlamayı teşvik etmek. Kazanılan puanlarla mağazadan
yeni temalar (Altın, Neon, Orman, Okyanus), ekstra mola hakkı ve rozetler
açılıyor.

## Telefona dokunulduğunu anlamak

Bir web uygulaması cihazın genel kullanımına erişemez. Kullanılabilecek en yakın
sinyal, sayfanın background'a geçip geçmediği. Kullanıcı başka bir uygulamaya
geçtiğinde tarayıcı `visibilitychange` event'ini tetikliyor:

```tsx
useEffect(() => {
  function onVisibilityChange() {
    if (document.hidden) markDistracted();
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return () => document.removeEventListener("visibilitychange", onVisibilityChange);
}, [markDistracted]);
```

Bu yaklaşık bir ölçüm: ekranın kapatılması da sayfayı gizliyor ve aynı event'i
tetikliyor. Gerçek bir screen time ölçümü için native API'lere erişim gerekiyor;
bu, store sürümünün yapılacaklar listesinde.

## Acil kişiler

Odak süresi boyunca uygulamanın diğer bölümleri kilitleniyor. Tek istisna
kullanıcının önceden eklediği acil kişiler; bu kişiler `tel:` link'iyle
aranabiliyor.

## Teknik yapı

- **Frontend.** Next.js App Router, TypeScript ve Tailwind CSS v4. Timer dairesel
  bir countdown animasyonuyla gösteriliyor.
- **State management.** Zustand. Puanlar, puan geçmişi, acil kişiler, satın
  alınanlar ve aktif tema `persist` middleware'i ile localStorage'da tutuluyor;
  backend ya da hesap gerekmiyor.
- **PWA.** Web manifest ve bir service worker sayesinde uygulama ana ekrana
  eklenebiliyor ve temel offline caching yapıyor.

## Kapanış

Uygulamanın bilinen eksikleri yol haritasını da belirliyor:

- **Timer drift.** Timer şu an kalan süreyi her saniye bir azaltıyor. Tarayıcılar
  background tab'lerde timer'ları throttle ettiği için süre kayabiliyor. Bitiş
  zamanını saklayıp kalan süreyi ondan hesaplamak daha doğru bir yöntem.
- **Bildirimler.** Süre dolduğunda push notification.
- **İstatistik ekranı.** Puan geçmişi zaten tutuluyor; yalnızca bir görünüm
  gerekiyor.
- **Native screen time.** Store sürümü için.

Bir özelliği "yaklaşık" yapmak sorun değil; önemli olan bunun kullanıcıya açıkça
söylenmesi.
