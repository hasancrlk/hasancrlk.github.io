---
title: "Bilgisayar Organizasyonu dersinden bir güneş takip sistemi"
kisa: Dört ışık sensörüyle güneşin yönünü bulup paneli iki servo motorla en verimli açıya çeviren Arduino prototipi.
ozet: "Bilgisayar Organizasyonu dersi için çift eksenli bir güneş takip sistemi geliştirdim. Dört ışık sensörü ve iki servo motorla çalışan prototipte en çok zaman alan konu servo titremesiydi."
date: 2026-08-07
teknolojiler: [Arduino, C++, LDR sensörler, SG90 servo, Seri haberleşme]
repo: https://github.com/hasancrlk/SolarTrack-Pro
kategori: donanim
sira: 10
ref: solartrack
---

Sabit bir güneş paneli güneşe yalnızca günün belirli bir bölümünde dik
bakar. Paneli güneşle birlikte döndürmek, aynı panelden daha fazla enerji
elde etmenin doğrudan bir yolu. SolarTrack Pro bu fikri iki eksende (sağ-sol
ve yukarı-aşağı) uygulayan bir prototip ve Bilgisayar Organizasyonu dersi
kapsamında geliştirildi.

## Donanım

- Arduino Uno R3
- 4 adet LDR ışık sensörü (sol, sağ, yukarı, aşağı)
- LDR'ler için 10K dirençlerle gerilim bölücü
- 2 adet SG90 mikro servo ve çift eksenli pan-tilt mekanizması
- 4.2V 100mA güneş paneli, breadboard ve bağlantı kabloları

## Çalışma prensibi

Dört sensör panelin dört kenarına yerleştirildi. Güneş tam karşıdayken
karşılıklı sensörler aynı ışık değerini okur. Güneş yer değiştirdikçe bir
taraf daha fazla ışık alır ve panel o yöne döndürülür. Yatay eksende sol ve
sağ sensörlerin farkına bakılıyor:

```cpp
int yatayFark = sol - sag;
if (yatayFark > ESIK && yatayAci < YATAY_MAX) {
  yatayAci += ADIM;
} else if (yatayFark < -ESIK && yatayAci > YATAY_MIN) {
  yatayAci -= ADIM;
}
```

Dikey eksende aynı mantık yukarı ve aşağı sensörlerle uygulanıyor.

## Servo titremesi

Prototipte en çok zaman alan sorun servo motorların titremesiydi. LDR
okumaları sürekli küçük dalgalanmalar gösteriyor. Sensörler arasındaki her
farka tepki verildiğinde servo, panel doğru konumdayken bile ileri geri
hareket ediyor.

Kodda bu soruna karşı iki sabit bulunuyor:

- **Eşik (`ESIK = 30`):** Karşılıklı sensörler arasındaki fark bu değeri
  aşmadıkça servo hareket etmiyor. Böylece ölçüm gürültüsü hareket olarak
  yansımıyor.
- **Adım (`ADIM = 1` derece):** Panel her döngüde yalnızca bir derece dönüyor.
  Büyük adımlar hedefin etrafında salınıma yol açabilir.

Servo açıları ayrıca 0–180 derece arasında sınırlandırıldı; böylece mekanizma
zorlanmıyor.

## Çalışma modları

Bulutlu havada ışık dağınık geldiği için sensörler net bir yön göstermiyor;
gece ise takip edilecek bir kaynak yok. Bu durumlarda panelin rastgele
dönmesi yerine ortada sabitlenmesi tercih edildi. Modlar seri port
üzerinden komutla değiştiriliyor:

- `MODE_SUN`: Aktif takip.
- `MODE_CLOUD` ve `MODE_NIGHT`: Servolar 90°/90° konumunda kilitli.
- `CENTER`: Servoları ortalar.
- `STOP` / `START`: Hareketi durdurur ya da yeniden başlatır.
- `DELAY_<ms>`: Sensör okuma aralığını 10–500 ms arasında değiştirir.

Kart her döngüde sensör değerlerini ve servo açılarını seri porta yazıyor.
Bu çıktı bir arayüz üzerinden okunup grafiğe dökülebiliyor.

## Geliştirilebilecek yönler

- Toplam ışık seviyesine bakarak bulut ve gece modunun otomatik seçilmesi.
- Panelin ürettiği gerilimin ölçülüp sabit bir panelle karşılaştırılması.
  Bu karşılaştırma sistemin sağladığı verim artışını sayısal olarak
  gösterecektir.
