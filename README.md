# OBD2 Veri Okuyucu

Bu proje, WiFi OBD2 cihazları için geliştirilmiş bir Python tabanlı veri okuma ve analiz aracıdır.

## Özellikler

- WiFi OBD2 bağlantısı
- Gerçek zamanlı veri okuma
- Çoklu protokol desteği
- Otomatik protokol tarama
- CAN mesajı çözümleme
- CSV formatında veri kaydı
- Kategorize edilmiş sensör verileri
- Terminal görünümü
- Koyu tema arayüz

## Desteklenen Sensörler

- Motor verileri (RPM, yük, tork, vb.)
- Sıcaklık sensörleri (motor, yağ, şanzıman, vb.)
- Yakıt sistemi (basınç, seviye, tüketim)
- Emisyon sistemi (O2, NOx, DPF, AdBlue)
- Hız ve mesafe bilgileri
- Akü ve alternatör verileri
- Motor zamanlama verileri (kam, krank, VVT)

## Gereksinimler

```bash
pip install PyQt5
```

## Kullanım

```bash
python3 obd_gui.py
```

## Protokol Desteği

- SAE J1850 PWM (41.6K)
- SAE J1850 VPW (10.4K)
- ISO 9141-2
- ISO 14230-4 KWP
- ISO 15765-4 CAN (11/29 bit, 250K/500K)
- SAE J1939 CAN

## Lisans

MIT License 