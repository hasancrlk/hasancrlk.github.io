---
title: "Güneşi takip eden panel: Arduino ile çift eksenli güneş takip sistemi"
kisa: Dört ışık sensörüyle güneşin yönünü bulup paneli iki servo motorla en verimli açıya çeviren Arduino prototipi.
ozet: "Dört ışık sensörü ve iki servo motorla güneşi takip eden bir güneş paneli prototipi yaptım. Kod kısa ama sensör gürültüsü, eşik ve çalışma modları gibi gerçek dünya sorunları öğretti."
date: 2026-08-07
teknolojiler: [Arduino, C++, LDR sensörler, SG90 servo, Seri haberleşme]
repo: https://github.com/hasancrlk/SolarTrack-Pro
kategori: donanim
sira: 10
ref: solartrack
---

## Fikir

Sabit bir güneş paneli güneşe yalnızca günün belli bir saatinde tam dik bakar.
Paneli güneşle birlikte döndürmek aynı panelden daha fazla enerji almanın en
doğrudan yolu. SolarTrack Pro bunu iki eksende (sağ-sol ve yukarı-aşağı)
yapan küçük bir prototip.

## Donanım

- Arduino Uno R3
- 4 adet LDR ışık sensörü: sol, sağ, yukarı, aşağı
- 10K dirençler (LDR'ler için gerilim bölücü)
- 2 adet SG90 mikro servo ve çift eksenli pan-tilt mekanizması
- 4.2V 100mA güneş paneli, breadboard ve kablolar

## Çalışma prensibi

Dört sensör paneli dört yönden çevreliyor. Güneş tam karşıdaysa karşılıklı
sensörler aynı ışığı görüyor. Güneş kaydıkça bir taraf daha aydınlık kalıyor
ve panel o tarafa dönüyor:

```cpp
int yatayFark = sol - sag;
if (yatayFark > ESIK && yatayAci < YATAY_MAX) {
  yatayAci += ADIM;
} else if (yatayFark < -ESIK && yatayAci > YATAY_MIN) {
  yatayAci -= ADIM;
}
```

Dikey eksen de aynı mantıkla yukarı ve aşağı sensörlerin farkına bakıyor.

## İki küçük ama önemli ayar

**Eşik (`ESIK = 30`).** Eşik olmadan servo, sensör okumalarındaki en küçük
gürültüde bile ileri geri titriyor. Fark belirli bir değeri aşmadan hareket
etmemek hem motoru hem enerjiyi koruyor.

**Adım (`ADIM = 1` derece).** Panel bir seferde büyük açılarla değil, birer
derece dönüyor. Hareket yumuşak oluyor ve hedefin etrafında salınım olmuyor.
Servo sınırları (0–180 derece) da mekanizmanın zorlanmasını önlüyor.

## Çalışma modları ve seri komutlar

Her zaman takip etmek mantıklı değil. Bulutlu havada ışık dağınık geliyor,
gece ise hiç yok. Bu durumlarda panelin rastgele dönmesi yerine ortaya
kilitlenmesi daha iyi:

| Komut | Etki |
|---|---|
| `MODE_SUN` | Güneş modu: aktif takip |
| `MODE_CLOUD` | Bulut modu: servolar 90°/90°'de kilitli |
| `MODE_NIGHT` | Gece modu: servolar 90°/90°'de kilitli |
| `CENTER` | Servoları ortala |
| `STOP` / `START` | Hareketi durdur / yeniden başlat |
| `DELAY_<ms>` | Sensör okuma sıklığını değiştir (10–500 ms) |

Kart her döngüde sensör değerlerini ve servo açılarını seri porttan yazıyor.
Bu satırlar bir arayüzde (dashboard) okunup grafiğe dökülebiliyor. Çıktının
biçimi şöyle (değerler örnek):

```
Sol:612 Sag:540 Yukari:701 Asagi:655 | YatayAci:94 DikeyAci:91
```

## Bir dahaki sefere

Şu an mod değişikliği elle yapılıyor. Toplam ışık seviyesinden gece ve bulut
modunu otomatik seçmek doğal bir sonraki adım. Panelin ürettiği gerilimi de
ölçüp sabit panelle karşılaştırmak, sistemin gerçekten ne kadar verim
kazandırdığını sayıyla gösterirdi.

## Öğrendiklerim

Yazılımda bir koşul ya doğrudur ya yanlış. Sensör dünyasında ise her okuma
biraz gürültülü. Eşik ve adım gibi iki küçük sabit, titreyen bir prototiple
düzgün çalışan bir sistem arasındaki farkı oluşturdu.
