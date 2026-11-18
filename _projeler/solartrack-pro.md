---
title: "Arduino ile Çift Eksenli Güneş Takip Sistemi: LDR, Servo ve Jitter Problemi"
kisa: Dört LDR sensörüyle güneşin yönünü bulup paneli iki servo motorla en verimli açıya çeviren bir Arduino prototipi.
ozet: "Sabit bir güneş paneli güneşe günün yalnızca bir bölümünde dik bakar. Paneli güneşle birlikte döndürmek aynı panelden daha fazla enerji almanın en doğrudan yolu; prototipte asıl zorluk ise kod değil, servo jitter'ı oldu."
date: 2026-08-07
teknolojiler: [Arduino, C++, LDR, SG90 servo, Serial]
repo: https://github.com/hasancrlk/SolarTrack-Pro
kategori: donanim
sira: 10
ref: solartrack
---

SolarTrack Pro, Bilgisayar Organizasyonu dersi için geliştirdiğim çift eksenli
(pan-tilt) bir güneş takip prototipi. Bu yazıda sistemin çalışma prensibini,
prototipte en çok uğraştıran servo jitter problemini ve çalışma modlarını
anlatıyorum.

## Donanım

- Arduino Uno R3
- 4 adet LDR (sol, sağ, yukarı, aşağı)
- LDR'ler için 10K dirençlerle voltage divider
- 2 adet SG90 micro servo ve pan-tilt mekanizması
- 4.2V 100mA güneş paneli, breadboard ve jumper kablolar

## Çalışma prensibi

Dört LDR panelin dört kenarına yerleştirildi. Güneş tam karşıdayken karşılıklı
sensörler aynı ışık değerini okur. Güneş yer değiştirdikçe bir taraf daha fazla
ışık alır ve panel o yöne döndürülür. Yatay eksende sol ve sağ sensörlerin farkına
bakılıyor:

```cpp
int yatayFark = sol - sag;
if (yatayFark > ESIK && yatayAci < YATAY_MAX) {
  yatayAci += ADIM;
} else if (yatayFark < -ESIK && yatayAci > YATAY_MIN) {
  yatayAci -= ADIM;
}
```

Dikey eksende aynı mantık yukarı ve aşağı sensörlerle uygulanıyor.

## Servo jitter problemi

LDR okumaları hiçbir zaman tam sabit değil; sürekli küçük dalgalanmalar (noise)
gösteriyor. Kod sensörler arasındaki her farka tepki verirse servo, panel doğru
konumdayken bile ileri geri titriyor. Prototipte en çok zaman alan konu bu oldu.

Kodda bu soruna karşı iki sabit var:

- **Threshold (`ESIK = 30`).** Karşılıklı sensörler arasındaki fark bu değeri
  aşmadıkça servo hareket etmiyor; ölçüm noise'u harekete dönüşmüyor.
- **Step (`ADIM = 1` derece).** Panel her loop'ta yalnızca bir derece dönüyor.
  Büyük adımlar hedefin etrafında oscillation'a yol açabilir.

Servo açıları ayrıca 0–180 derece arasında sınırlandırıldı; mekanizma
zorlanmıyor.

## Çalışma modları ve serial komutlar

Bulutlu havada ışık dağınık geliyor ve sensörler net bir yön göstermiyor; gece
ise takip edilecek bir kaynak yok. Bu durumlarda panelin rastgele dönmesi yerine
merkezde kilitlenmesi tercih edildi. Modlar serial port üzerinden komutla
değiştiriliyor:

- **`MODE_SUN`.** Aktif takip.
- **`MODE_CLOUD` / `MODE_NIGHT`.** Servolar 90°/90° konumunda kilitli.
- **`CENTER`.** Servoları merkeze alır.
- **`STOP` / `START`.** Hareketi durdurur ya da yeniden başlatır.
- **`DELAY_<ms>`.** Sensör okuma aralığını 10–500 ms arasında ayarlar.

Kart her loop'ta sensör değerlerini ve servo açılarını serial porta yazıyor;
bu çıktı bir dashboard üzerinden okunup grafiğe dökülebiliyor.

## Kapanış

Prototipin geliştirilebilecek iki yönü var: toplam ışık seviyesine bakarak bulut
ve gece modunun otomatik seçilmesi, ve panelin ürettiği voltajın ölçülüp sabit bir
panelle karşılaştırılması. İkincisi, sistemin sağladığı verim artışını sayısal
olarak göstermenin tek yolu.

Yazılımda bir koşul ya doğrudur ya yanlış; sensörlerle çalışırken ise her okuma
biraz noise içerir. Threshold ve step gibi iki küçük sabit, titreyen bir
prototiple düzgün çalışan bir sistem arasındaki farkı oluşturuyor.
