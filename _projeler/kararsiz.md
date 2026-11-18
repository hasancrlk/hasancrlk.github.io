---
title: "Yurtta siparişi kim alacak? Kararsız uygulamasının hikâyesi."
kisa: Herkes parmağını ekrana koyar, uygulama countdown sonunda birini rastgele seçer. KYK yurdundaki bir ihtiyaçtan doğdu.
ozet: "KYK yurdunda dışarıdan yemek söylediğimizde birinin güvenliğe inip siparişi alması gerekiyordu. Kimin ineceğine bu tarz bir uygulamayla karar veriyorduk. Peki neden kendim de yapmayayım ki?"
date: 2026-08-08
teknolojiler: [React Native, Expo, expo-router, expo-haptics, TypeScript]
repo: https://github.com/hasancrlk/Kararsiz
kategori: mobil-web
sira: 9
ref: kararsiz
---

Kararsız, Expo ve React Native ile geliştirdiğim küçük bir multi-touch
uygulaması. Herkes parmağını telefonun ekranına koyuyor, kısa bir countdown'dan
sonra uygulama bir parmağı rastgele seçiyor. Adı da bu kullanımdan geliyor: bir
seçim yapmanız gerektiğinde ama kararsız kaldığınızda, seçenekleri parmaklara
paylaştırıp sonucu uygulamaya bırakabiliyorsunuz.

Bu yazıda uygulamanın akışını, multi-touch takibini ve React'te karşılaşılan
stale closure problemini anlatıyorum.

## Akış

1. **Başla** butonuna basılıyor.
2. 2 ile 10 kişi parmağını ekrana koyuyor.
3. İkinci parmak ekrana değdiği anda 3 saniyelik countdown başlıyor; her saniyede
   telefon titriyor.
4. Countdown bitince parmaklardan biri rastgele seçiliyor. Seçilen parmağın
   halkası büyüyor ve telefon sürekli titriyor.
5. Herkes parmağını çektiğinde oyun sıfırlanıyor.

## Multi-touch takibi

Ekrandaki her touch event'inin benzersiz bir `identifier` değeri var. Parmaklar
bu değerle bir `Map` içinde tutuluyor. Hareket eden parmağın yalnızca koordinatı
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

Countdown sırasında bir parmak kalkar ve ekranda hâlâ en az iki parmak varsa
countdown baştan başlıyor; ikiden az parmak kalırsa iptal ediliyor.

## Stale closure problemi

Touch handler'ları `useCallback` ile bir kez oluşturuluyor. Handler içinde
doğrudan `phase` state'i okunursa, fonksiyonun oluşturulduğu andaki değer görülür.
React'te buna **stale closure** denir ve countdown devam ederken ikinci bir
countdown'ın başlamasına yol açabilir.

Çözüm olarak oyun aşaması bir `useRef` içinde de tutuluyor. Render'ı `phase`
state'i yönetiyor; handler'lar ise her zaman güncel olan `phaseRef.current`
değerini okuyor:

```tsx
const [phase, setPhase] = useState<'idle' | 'countdown' | 'selected'>('idle');
const phaseRef = useRef<'idle' | 'countdown' | 'selected'>('idle');

if (updated.size >= 2 && phaseRef.current === 'idle') {
  startCountdown(updated);
}
```

## Haptic feedback

`expo-haptics` ile countdown'ın her saniyesinde medium şiddette bir titreşim,
seçim anında bir success titreşimi ve kazanan parmak ekranda kaldığı sürece
tekrarlayan güçlü bir titreşim veriliyor. Telefon masanın ortasında dururken
sonucun hissedilmesi oyunun en önemli parçası.

## Kapanış

Kararsız küçük bir uygulama, ama event handler'lar, timer'lar ve state aynı anda
değiştiğinde "handler hangi değeri görüyor?" sorusunun ne kadar kritik olduğunu
göstermesi açısından iyi bir örnek. Multi-touch davranışı web ve mobilde farklı
olduğu için de gerçek cihazda test etmek şart.
