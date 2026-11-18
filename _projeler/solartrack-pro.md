---
title: "Bilgisayar Organizasyonu dersinden bir güneş takip sistemi"
kisa: Dört ışık sensörüyle güneşin yönünü bulup paneli iki servo motorla en verimli açıya çeviren Arduino prototipi.
ozet: "Sabit bir güneş paneli güneşe günün yalnızca bir bölümünde dik bakar. Paneli güneşle birlikte döndürsek? Bilgisayar Organizasyonu dersi için bunu iki eksende yapan bir prototip kurdum."
date: 2026-08-07
teknolojiler: [Arduino, C++, LDR sensörler, SG90 servo, Seri haberleşme]
repo: https://github.com/hasancrlk/SolarTrack-Pro
kategori: donanim
sira: 10
ref: solartrack
---

SolarTrack Pro paneli hem sağa-sola hem yukarı-aşağı döndürüyor. Kodu kısa,
ama beni en çok uğraştıran şey kod değil, servo motorların titremesi oldu.

## Kullandığım parçalar

- Arduino Uno R3
- 4 adet LDR ışık sensörü (sol, sağ, yukarı, aşağı)
- LDR'ler için 10K dirençlerle gerilim bölücü
- 2 adet SG90 mikro servo ve çift eksenli pan-tilt mekanizması
- 4.2V 100mA güneş paneli, breadboard ve bağlantı kabloları

## Panel güneşi nasıl buluyor?

Dört sensörü panelin dört kenarına yerleştirdim. Güneş tam karşıdayken
karşılıklı sensörler aynı ışığı görüyor. Güneş kaydıkça bir taraf daha fazla
ışık alıyor ve panel o tarafa dönüyor. Yatay eksende sol ve sağ sensörlerin
farkına bakıyorum:

```cpp
int yatayFark = sol - sag;
if (yatayFark > ESIK && yatayAci < YATAY_MAX) {
  yatayAci += ADIM;
} else if (yatayFark < -ESIK && yatayAci > YATAY_MIN) {
  yatayAci -= ADIM;
}
```

Dikey eksende de aynı mantık yukarı ve aşağı sensörlerle çalışıyor.

## Servo titremesi

LDR okumaları hiçbir zaman tam sabit değil, sürekli küçük dalgalanmalar
gösteriyor. Kod sensörler arasındaki her farka tepki verirse servo, panel
doğru yerdeyken bile ileri geri oynuyor. Prototipte en çok bununla uğraştım.

Kodda buna karşı iki sabit var:

- **Eşik (`ESIK = 30`):** Karşılıklı sensörler arasındaki fark bu değeri
  geçmedikçe servo kıpırdamıyor. Böylece ölçüm gürültüsü harekete
  dönüşmüyor.
- **Adım (`ADIM = 1` derece):** Panel her döngüde yalnızca bir derece
  dönüyor. Büyük adımlar hedefin etrafında salınıma yol açabilir.

Servo açılarını ayrıca 0–180 derece arasında sınırladım ki mekanizma
zorlanmasın.

## Hava kapalıysa ne olacak?

Bulutlu havada ışık dağınık geliyor ve sensörler net bir yön göstermiyor;
gece ise takip edecek bir şey yok. Bu durumlarda panelin rastgele dönmesi
yerine ortada durmasını tercih ettim. Modları seri porttan komutla
değiştirebiliyorsunuz:

- `MODE_SUN`: Aktif takip.
- `MODE_CLOUD` ve `MODE_NIGHT`: Servolar 90°/90°'de kilitli.
- `CENTER`: Servoları ortalıyor.
- `STOP` / `START`: Hareketi durdurup yeniden başlatıyor.
- `DELAY_<ms>`: Sensör okuma aralığını 10–500 ms arasında ayarlıyor.

Kart her döngüde sensör değerlerini ve servo açılarını seri porta yazıyor,
böylece bu değerler bir arayüzde okunup grafiğe dökülebiliyor.

## Geliştirilebilecek yönler

Şu an modu elle seçiyorsunuz; toplam ışık seviyesine bakıp bulut ve gece
modunu kendiliğinden seçmek ilk adım olur. Panelin ürettiği gerilimi ölçüp
sabit bir panelle karşılaştırmak da sistemin ne kadar verim kazandırdığını
sayıyla gösterir.
