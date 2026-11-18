---
title: "Yurtta yemeği kim alacak? Kararsız uygulamasının hikâyesi"
kisa: Herkes parmağını ekrana koyar, uygulama geri sayımla birini rastgele seçer. KYK yurdundaki bir ihtiyaçtan doğdu.
ozet: "KYK yurdunda dışarıdan yemek söylediğimizde birinin güvenliğe inip siparişi alması gerekiyordu. Kimin ineceğine bu uygulamayla karar veriyorduk."
date: 2026-08-08
teknolojiler: [React Native, Expo, expo-router, expo-haptics, TypeScript]
repo: https://github.com/hasancrlk/Kararsiz
kategori: mobil-web
sira: 9
ref: kararsiz
---

KYK yurdunda dışarıdan yemek söylediğimizde sipariş odaya kadar gelmiyordu;
birinin güvenliğe inip alması gerekiyordu. Kimin ineceğine karar vermek için
bu uygulamayı yazdım. Herkes parmağını telefonun ekranına koyuyor, kısa bir
geri sayımdan sonra uygulama bir parmağı seçiyor ve aşağı inecek kişi
belli oluyor.

Uygulamanın adı da bu kullanımdan geliyor: bir seçim yapmanız gerektiğinde
ama kararsız kaldığınızda, seçenekleri parmaklara paylaştırıp sonucu
uygulamaya bırakabiliyorsunuz.

## Nasıl çalışıyor

1. **Başla** düğmesine basılıyor.
2. 2 ile 10 kişi parmağını ekrana koyuyor.
3. İkinci parmak ekrana değdiği anda 3 saniyelik geri sayım başlıyor ve her
   saniyede telefon titriyor.
4. Geri sayım bitince parmaklardan biri rastgele seçiliyor. Seçilen parmağın
   halkası büyüyor ve telefon sürekli titriyor.
5. Herkes parmağını çektiğinde oyun sıfırlanıyor.

## Parmakların takibi

Ekrandaki her dokunuşun benzersiz bir `identifier` değeri var. Parmaklar bu
değerle bir `Map` içinde tutuluyor. Hareket eden parmağın yalnızca konumu
güncelleniyor; yeni gelen parmağa bir renk atanıyor:

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

Geri sayım sırasında bir parmak kalkar ve ekranda hâlâ en az iki parmak
varsa geri sayım baştan başlıyor. İkiden az parmak kalırsa sayım iptal
ediliyor.

## Durumun güncel okunması

Dokunma işleyicileri `useCallback` ile bir kez oluşturuluyor. İçlerinde
doğrudan `phase` durumu okunursa, işleyicinin oluşturulduğu andaki değer
görülür. React'te bu durum "bayat kapanış" (stale closure) olarak bilinir ve
geri sayım devam ederken ikinci bir geri sayımın başlamasına yol açabilir.

Bu nedenle oyun aşaması bir `useRef` içinde de tutuluyor. Ekranı çizen
`phase` durumu, işleyicilerin okuduğu ise her zaman güncel olan
`phaseRef.current`:

```tsx
const [phase, setPhase] = useState<'idle' | 'countdown' | 'selected'>('idle');
const phaseRef = useRef<'idle' | 'countdown' | 'selected'>('idle');

if (updated.size >= 2 && phaseRef.current === 'idle') {
  startCountdown(updated);
}
```

## Titreşim

`expo-haptics` ile geri sayımın her saniyesinde orta şiddette bir titreşim,
seçim anında bir başarı titreşimi ve kazanan parmak ekranda kaldığı sürece
tekrarlayan güçlü bir titreşim veriliyor. Telefon masanın ortasında dururken
sonucun hissedilmesi oyunun en önemli parçası.

Uygulamayı gerçek telefonda ilk denediğimizde sonuç hoşuma gitti.
