import socket
import time
import csv
from datetime import datetime
import os

class OBD2Connection:
    def __init__(self, ip="192.168.0.10", port=35000):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
        self.pid_commands = {
            'RPM': '010C',         # Motor RPM
            'SPEED': '010D',       # Araç Hızı
            'TEMP': '0105',        # Motor Soğutma Suyu Sıcaklığı
            'LOAD': '0104',        # Motor Yükü
            'THROTTLE': '0111'     # Gaz Pedalı Pozisyonu
        }
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            self.socket.settimeout(5.0)  # 5 saniye timeout
            print(f"Bağlantı başarılı: {self.ip}:{self.port}")
            
            # Initialize ELM327
            print("\nELM327 Başlatılıyor...")
            
            # Reset ve Echo off
            print("Reset yapılıyor...")
            self._send_command("ATZ")    # Reset
            time.sleep(2)  # Reset için daha uzun bekle
            self._send_command("ATE0")   # Echo off
            
            # Cihaz bilgilerini al
            print("\nCihaz Bilgileri:")
            response = self._send_command("ATI")
            print(f"Cihaz: {response}")
            
            # Protokol ayarları
            print("\nProtokolü Ayarlama:")
            self._send_command("ATL0")   # Linefeeds off
            self._send_command("ATH0")   # Headers off
            self._send_command("ATS0")   # Spaces off
            
            # Önce otomatik protokol dene
            print("Otomatik protokol deneniyor...")
            self._send_command("ATSP0")
            time.sleep(1)
            
            # Protokol durumunu kontrol et
            response = self._send_command("ATDP")
            print(f"Aktif Protokol: {response}")
            
            if "ISO 15765-4 (CAN 11/500)" not in response:
                print("CAN protokolüne geçiliyor...")
                self._send_command("ATSP6")  # ISO 15765-4, CAN (11/500)
                time.sleep(1)
                response = self._send_command("ATDP")
                print(f"Yeni Protokol: {response}")
            
            # Desteklenen PID'leri kontrol et
            print("\nDesteklenen PID'ler kontrol ediliyor...")
            response = self._send_command("0100")
            if response and "NO DATA" not in response:
                print("PID Desteği: OK")
            else:
                print("UYARI: PID desteği alınamadı!")
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Bağlantı hatası: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.connected = False
            print("Bağlantı kapatıldı")
    
    def _send_command(self, command, retries=3):
        if not self.socket:
            print("Bağlantı yok!")
            return None
        
        for attempt in range(retries):
            try:
                self.socket.send((command + "\r").encode())
                response = self.socket.recv(1024).decode().strip()
                
                if "ERROR" in response or "UNABLE TO CONNECT" in response:
                    if attempt == retries - 1:  # Son denemede ise hata göster
                        print(f"Komut hatası ({command}): {response}")
                    time.sleep(0.5)  # Hatadan sonra biraz bekle
                    continue
                    
                return response
            except socket.timeout:
                if attempt == retries - 1:  # Son denemede ise hata göster
                    print(f"Timeout hatası (Deneme {attempt + 1}/{retries})")
                time.sleep(0.5)
                continue
            except Exception as e:
                print(f"Komut gönderme hatası: {str(e)}")
                return None
        return None

    def parse_response(self, pid, response):
        try:
            if not response or "NO DATA" in response:
                return None
                
            # Hex string'i temizle
            data = response.split('\r')[-1]  # Son satırı al
            data = ''.join(c for c in data if c.isalnum())  # Sadece alfanumerik karakterleri al
            
            if len(data) < 4:  # Minimum uzunluk kontrolü
                return None
                
            if pid == 'RPM':  # 010C
                if len(data) >= 8:
                    a = int(data[4:6], 16)
                    b = int(data[6:8], 16)
                    return ((a * 256) + b) / 4
            elif pid == 'SPEED':  # 010D
                if len(data) >= 6:
                    return int(data[4:6], 16)
            elif pid == 'TEMP':  # 0105
                if len(data) >= 6:
                    return int(data[4:6], 16) - 40
            elif pid == 'LOAD':  # 0104
                if len(data) >= 6:
                    return (int(data[4:6], 16) * 100) / 255
            elif pid == 'THROTTLE':  # 0111
                if len(data) >= 6:
                    return (int(data[4:6], 16) * 100) / 255
                
            return None
                
        except Exception as e:
            if "invalid literal for int()" not in str(e):  # Sadece önemli hataları göster
                print(f"Veri ayrıştırma hatası ({pid}): {str(e)}")
            return None

    def read_all_data(self):
        data = {'timestamp': datetime.now().isoformat()}
        
        for pid_name, pid_code in self.pid_commands.items():
            response = self._send_command(pid_code)
            value = self.parse_response(pid_name, response)
            data[pid_name] = value
            time.sleep(0.1)  # Her PID sorgusu arasında kısa bekleme
            
        return data

def create_log_file():
    # Logs klasörü oluştur
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Timestamp ile yeni dosya oluştur
    filename = f"logs/obd2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return filename

def main():
    obd = OBD2Connection()
    
    if obd.connect():
        try:
            # Log dosyası oluştur
            log_file = create_log_file()
            print(f"\nVeriler {log_file} dosyasına kaydedilecek")
            
            # CSV başlıklarını yaz
            headers = ['timestamp'] + list(obd.pid_commands.keys())
            with open(log_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            
            print("\nVeri okuma başladı. Durdurmak için Ctrl+C'ye basın...")
            
            while True:
                try:
                    # Tüm verileri oku
                    data = obd.read_all_data()
                    
                    # Ekrana yazdır
                    print("\nOkunan Veriler:")
                    for key, value in data.items():
                        if key != 'timestamp':
                            print(f"{key}: {value if value is not None else 'Okunamadı'}")
                    
                    # CSV'ye kaydet
                    with open(log_file, 'a', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writerow(data)
                    
                    time.sleep(2)  # 2 saniye bekle
                    
                except KeyboardInterrupt:
                    print("\nVeri okuma durduruldu")
                    break
                    
        finally:
            obd.disconnect()

if __name__ == "__main__":
    main() 