---
title: "Parmağını ekrana koy: çoklu dokunmayla rastgele seçici Kararsız"
kisa: Herkes parmağını ekrana koyar, uygulama geri sayımla birini rastgele seçer. Expo ve React Native ile çoklu dokunma.
ozet: "Kimin bulaşık yıkayacağına karar veremeyen arkadaş grupları için küçük bir mobil oyun yaptım. Küçük ama çoklu dokunmayı ve React'teki bayat durum tuzağını öğreten bir proje oldu."
date: 2026-08-08
teknolojiler: [React Native, Expo, expo-router, expo-haptics, TypeScript]
repo: https://github.com/hasancrlk/Kararsiz
kategori: mobil-web
sira: 9
ref: kararsiz
---

## Fikir

"Kim ödeyecek?", "ilk kim başlayacak?" Herkes parmağını telefonun ekranına
koyar, kısa bir geri sayımdan sonra uygulama bir parmağı seçer. Seçilen
parmağın halkası büyür ve telefon titrer.

1. **Başla**'ya basılır.
2. 2 ile 10 kişi parmağını ekrana koyar.
3. İkinci parmak değdiği anda 3 saniyelik geri sayım başlar. Her saniyede
   titreşim var.
4. Geri sayım bitince bir parmak rastgele seçilir.
5. Herkes parmağını çekince oyun sıfırlanır.

## Her parmağı ayrı takip etmek

Ekrandaki her dokunuşun bir `identifier` değeri var. Parmakları bu kimlikle
bir `Map` içinde tutuyorum. Parmak hareket ederse yalnızca koordinatı
güncelleniyor, yeni bir parmak gelirse renk atanıp listeye ekleniyor:

```tsx
touches.forEach((t) => {
  const id = String(t.identifier);
  if (updated.has(id)) {
    updated.set(id, { ...updated.get(id)!, x: t.pageX, y: t.pageY });
  } else if (updated.size < MAX_FINGERS) {
    updated.set(id, { id, x: t.pageX, y: t.pageY,
                      colorIndex: updated.size % COLORS.length, isWinner: false });
  }
});
```

Geri sayım sırasında biri parmağını çekerse ve ekranda hâlâ en az iki kişi
varsa geri sayım baştan başlıyor. İkiden az kişi kalırsa iptal ediliyor. Son
parmak da kalkınca her şey sıfırlanıyor.

## Bayat durum tuzağı

Projenin bana öğrettiği asıl şey buydu. Dokunma işleyicileri `useCallback`
ile bir kez oluşturuluyor. İçlerinde `phase` durumunu okursam, fonksiyonun
oluşturulduğu andaki değeri görüyorlar. Buna React'te "bayat kapanış" (stale
closure) deniyor. Sonuç: geri sayım başlamış olmasına rağmen işleyici hâlâ
"boştayım" sanıp ikinci bir geri sayım başlatabiliyordu.

Çözüm, durumu bir de `useRef` içinde tutmak. Ekranı çizen `phase` durumu,
işleyicilerin okuduğu ise her zaman güncel olan `phaseRef.current`:

```tsx
const [phase, setPhase] = useState<'idle' | 'countdown' | 'selected'>('idle');
const phaseRef = useRef<'idle' | 'countdown' | 'selected'>('idle');
// ...
if (updated.size >= 2 && phaseRef.current === 'idle') {
  startCountdown(updated);
}
```

## Dokunsal geri bildirim

`expo-haptics` ile geri sayımın her saniyesinde orta şiddette titreşim, seçim
anında "başarı" titreşimi ve kazanan parmak ekranda kaldıkça tekrarlayan güçlü
bir titreşim var. Telefon masada dururken bile sonucun hissedilmesi oyunu
eğlenceli yapan şey.

## Öğrendiklerim

Küçük bir oyun, React'in zamanlama modelini öğrenmek için en iyi yerlerden
biri çıktı. Olay işleyicileri, zamanlayıcılar ve durum aynı anda
değiştiğinde "hangi değeri görüyorum?" sorusu kritik hâle geliyor. Bir de
çoklu dokunmanın web'de ve mobilde farklı davrandığını, gerçek cihazda
denemeden emin olunamayacağını öğrendim.
