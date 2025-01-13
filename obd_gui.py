import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                           QGridLayout, QProgressBar, QMessageBox, QTabWidget,
                           QTextEdit, QSplitter, QComboBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor
import socket
import time
from datetime import datetime
import csv

# CAN mesaj formatları
CAN_FORMATS = {
    'STANDART': {
        'description': 'Standart CAN (11-bit ID)',
        'id_length': 11,
        'example': '7E8 03 41 0C 1A F8'
    },
    'EXTENDED': {
        'description': 'Extended CAN (29-bit ID)',
        'id_length': 29,
        'example': '18DAF110 03 41 0C 1A F8'
    }
}

# OBD Protokolleri
OBD_PROTOCOLS = {
    'AUTO': ('ATSP0', 'Otomatik Protokol Seçimi'),
    'SAE_J1850_PWM': ('ATSP1', 'SAE J1850 PWM (41.6K)'),
    'SAE_J1850_VPW': ('ATSP2', 'SAE J1850 VPW (10.4K)'),
    'ISO_9141_2': ('ATSP3', 'ISO 9141-2 (5 baud init)'),
    'ISO_14230_4_5B': ('ATSP4', 'ISO 14230-4 KWP (5 baud init)'),
    'ISO_14230_4_FB': ('ATSP5', 'ISO 14230-4 KWP (fast init)'),
    'ISO_15765_4_11B_500K': ('ATSP6', 'ISO 15765-4 CAN (11 bit, 500K)'),
    'ISO_15765_4_29B_500K': ('ATSP7', 'ISO 15765-4 CAN (29 bit, 500K)'),
    'ISO_15765_4_11B_250K': ('ATSP8', 'ISO 15765-4 CAN (11 bit, 250K)'),
    'ISO_15765_4_29B_250K': ('ATSP9', 'ISO 15765-4 CAN (29 bit, 250K)'),
    'SAE_J1939_29B_250K': ('ATSPA', 'SAE J1939 CAN (29 bit, 250K)')
}

class TerminalWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont('Courier New', 10))
        self.setStyleSheet("background-color: #1E1E1E; color: #00FF00;")
        self.setMinimumHeight(150)
    
    def append_message(self, message, message_type="info"):
        color = {
            "info": "#00FF00",    # Yeşil
            "error": "#FF0000",   # Kırmızı
            "warning": "#FFA500", # Turuncu
            "rx": "#00FFFF",      # Açık Mavi (Alınan veri)
            "tx": "#FFB6C1"       # Açık Pembe (Gönderilen veri)
        }.get(message_type, "#FFFFFF")
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.append(f'<font color="{color}">[{timestamp}] {message}</font>')
        self.moveCursor(QTextCursor.End)

class CANDecoder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # CAN Format seçimi
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(CAN_FORMATS.keys())
        format_layout.addWidget(QLabel("CAN Format:"))
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        # CAN mesaj girişi
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Örn: 7E8 03 41 0C 1A F8")
        self.decode_btn = QPushButton("Decode")
        self.decode_btn.clicked.connect(self.decode_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.decode_btn)
        layout.addLayout(input_layout)
        
        # Sonuç gösterimi
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # Örnek format gösterimi
        self.example_label = QLabel()
        self.update_example()
        layout.addWidget(self.example_label)
        
        self.format_combo.currentTextChanged.connect(self.update_example)
    
    def update_example(self):
        current_format = CAN_FORMATS[self.format_combo.currentText()]
        self.example_label.setText(f"Örnek format: {current_format['example']}")
        self.message_input.setPlaceholderText(f"Örn: {current_format['example']}")
    
    def decode_message(self):
        message = self.message_input.text().strip()
        if not message:
            return
        
        try:
            # Mesajı parçalara ayır
            parts = message.split()
            if not parts:
                raise ValueError("Geçersiz mesaj formatı")
            
            # CAN ID'yi parse et
            can_id = parts[0]
            data_bytes = parts[1:]
            
            result = []
            result.append(f"CAN ID: {can_id}")
            result.append(f"Uzunluk: {len(data_bytes)} byte")
            
            if len(data_bytes) > 0:
                # OBD2 cevap formatı: ilk byte uzunluk, ikinci byte mod+40h, üçüncü byte PID
                if len(data_bytes) >= 3 and data_bytes[1].startswith('4'):
                    mode = int(data_bytes[1], 16) - 0x40
                    pid = data_bytes[2]
                    result.append(f"\nOBD2 Yanıt Analizi:")
                    result.append(f"Mode: {mode:02X}h")
                    result.append(f"PID: {pid}h")
                    
                    # Veri baytlarını analiz et
                    if len(data_bytes) > 3:
                        data_values = data_bytes[3:]
                        result.append("\nVeri Baytları:")
                        for i, value in enumerate(data_values):
                            result.append(f"Byte {i+1}: {value}h ({int(value, 16)}d)")
                
                # Ham veri gösterimi
                result.append("\nHam Veri:")
                result.append(" ".join(data_bytes))
            
            self.result_text.setText("\n".join(result))
            
        except Exception as e:
            self.result_text.setText(f"Hata: {str(e)}")

class OBD2Reader(QThread):
    data_received = pyqtSignal(dict)
    connection_error = pyqtSignal(str)
    
    def __init__(self, obd_connection):
        super().__init__()
        self.obd = obd_connection
        self.running = False
        self.mutex = QMutex()
    
    def run(self):
        with QMutexLocker(self.mutex):
            self.running = True
            
        while True:
            with QMutexLocker(self.mutex):
                if not self.running:
                    break
                    
            try:
                if self.obd.connected:
                    data = self.obd.read_all_data()
                    self.data_received.emit(data)
                time.sleep(1)
            except Exception as e:
                self.connection_error.emit(str(e))
                break
    
    def stop(self):
        with QMutexLocker(self.mutex):
            self.running = False

class ProtocolScanner(QThread):
    protocol_found = pyqtSignal(str, str)
    scan_complete = pyqtSignal()
    
    def __init__(self, obd_connection):
        super().__init__()
        self.obd = obd_connection
        self.running = False
        self.mutex = QMutex()
    
    def run(self):
        with QMutexLocker(self.mutex):
            self.running = True
        
        try:
            for protocol_name, (command, description) in OBD_PROTOCOLS.items():
                with QMutexLocker(self.mutex):
                    if not self.running:
                        break
                    
                if protocol_name != 'AUTO':
                    self.obd._send_command(command)
                    time.sleep(1)
                    
                    response = self.obd._send_command("010C")
                    if response and "NO DATA" not in response and "ERROR" not in response:
                        self.protocol_found.emit(protocol_name, description)
        finally:
            self.scan_complete.emit()
    
    def stop(self):
        with QMutexLocker(self.mutex):
            self.running = False

class OBD2Connection:
    def __init__(self, ip="192.168.0.10", port=35000):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
        self.terminal = None  # Terminal referansı
        self.current_protocol = 'AUTO'
        
        # Genişletilmiş PID kategorileri
        self.pid_categories = {
            'MOTOR_TEMEL': {
                'RPM': ('010C', 'Motor Devri', 'RPM', 8000),
                'LOAD': ('0104', 'Motor Yükü', '%', 100),
                'MAP': ('010B', 'Manifold Basıncı', 'kPa', 255),
                'MAF': ('0110', 'Hava Akış', 'g/s', 655.35),
                'TIMING_ADV': ('010E', 'Ateşleme Avansı', '°', 180),
                'THROTTLE': ('0111', 'Gaz Pedalı', '%', 100),
                'ENGINE_TORQUE': ('0163', 'Motor Torku', 'Nm', 500)
            },
            'MOTOR_DETAY': {
                'INTAKE_TEMP': ('010F', 'Emme Sıcaklığı', '°C', 150),
                'BAROMETRIC': ('0133', 'Barometrik Basınç', 'kPa', 255),
                'RELATIVE_THROTTLE': ('0145', 'Relatif Gaz', '%', 100),
                'AMBIENT_TEMP': ('0146', 'Dış Sıcaklık', '°C', 150),
                'COMMANDED_THROTTLE': ('014C', 'İstenen Gaz', '%', 100),
                'ACCEL_POSITION': ('0149', 'Gaz Pedalı D', '%', 100),
                'ACCEL_POSITION_E': ('014A', 'Gaz Pedalı E', '%', 100),
                'ACCEL_POSITION_F': ('014B', 'Gaz Pedalı F', '%', 100)
            },
            'SICAKLIK': {
                'COOLANT_TEMP': ('0105', 'Soğutma Suyu', '°C', 150),
                'OIL_TEMP': ('015C', 'Yağ Sıcaklığı', '°C', 150),
                'TRANS_TEMP': ('015C', 'Şanzıman Sıc.', '°C', 150),
                'INTAKE_TEMP': ('010F', 'Emme Sıcaklığı', '°C', 150),
                'FUEL_TEMP': ('015F', 'Yakıt Sıcaklığı', '°C', 150),
                'CATALYST_TEMP_B1S1': ('013C', 'Katalizör B1S1', '°C', 1000),
                'CATALYST_TEMP_B1S2': ('013D', 'Katalizör B1S2', '°C', 1000),
                'CATALYST_TEMP_B2S1': ('013E', 'Katalizör B2S1', '°C', 1000),
                'CATALYST_TEMP_B2S2': ('013F', 'Katalizör B2S2', '°C', 1000)
            },
            'YAKIT': {
                'FUEL_PRESSURE': ('010A', 'Yakıt Basıncı', 'kPa', 765),
                'FUEL_RAIL_PRESSURE': ('0123', 'Rail Basıncı', 'kPa', 655350),
                'FUEL_RAIL_PRESSURE_ABS': ('0159', 'Rail Abs Basınç', 'kPa', 655350),
                'FUEL_LEVEL': ('012F', 'Yakıt Seviyesi', '%', 100),
                'FUEL_RATE': ('015E', 'Yakıt Tüketimi', 'L/h', 100),
                'FUEL_TYPE': ('0151', 'Yakıt Tipi', '-', 0),
                'ETHANOL_FUEL': ('0152', 'Etanol Oranı', '%', 100)
            },
            'HIZ_MESAFE': {
                'SPEED': ('010D', 'Araç Hızı', 'km/h', 220),
                'DISTANCE': ('0131', 'Mesafe', 'km', 0),
                'DISTANCE_W_MIL': ('0121', 'MIL Sonrası Mes.', 'km', 0),
                'RUNTIME': ('011F', 'Çalışma Süresi', 'sn', 0),
                'RUNTIME_W_MIL': ('014D', 'MIL Süresi', 'dk', 0),
                'TIME_SINCE_CODES_CLR': ('014E', 'DTC Sil Sonrası', 'dk', 0)
            },
            'EMISYON_TEMEL': {
                'O2_B1S1_VOLTAGE': ('0114', 'O2 B1S1 Voltaj', 'V', 5),
                'O2_B1S2_VOLTAGE': ('0115', 'O2 B1S2 Voltaj', 'V', 5),
                'O2_B2S1_VOLTAGE': ('0116', 'O2 B2S1 Voltaj', 'V', 5),
                'O2_B2S2_VOLTAGE': ('0117', 'O2 B2S2 Voltaj', 'V', 5),
                'EGR_ERROR': ('012C', 'EGR Hata', '%', 100),
                'EVAP_PRESSURE': ('0132', 'EVAP Basıncı', 'Pa', 8192),
                'COMMANDED_EGR': ('012C', 'EGR Komutu', '%', 100),
                'COMMANDED_EVAP': ('012E', 'EVAP Komutu', '%', 100)
            },
            'EMISYON_DETAY': {
                'NOX_SENSOR': ('0183', 'NOx Sensörü', 'ppm', 1000),
                'NOX_SENSOR_ALT': ('0184', 'NOx Sensör Alt', 'ppm', 1000),
                'PM_SENSOR': ('0182', 'PM Sensörü', 'mg/m³', 100),
                'UREA_LEVEL': ('0162', 'AdBlue Seviyesi', '%', 100),
                'DPF_PRESSURE': ('0178', 'DPF Basıncı', 'kPa', 100),
                'DPF_TEMP': ('0177', 'DPF Sıcaklığı', '°C', 1000),
                'DPF_REGEN_STATUS': ('0185', 'DPF Rejenerasyon', '-', 0),
                'SCR_INDUCEMENT': ('0188', 'SCR Durum', '-', 0)
            },
            'MOTOR_ZAMANLAMA': {
                'TIMING_ADVANCE': ('010E', 'Ateşleme Avans', '°', 180),
                'CAM_POSITION_B1': ('0161', 'Kam B1 Konum', '°', 360),
                'CAM_POSITION_B2': ('0165', 'Kam B2 Konum', '°', 360),
                'CRANK_POSITION': ('0167', 'Krank Konum', '°', 360),
                'VVT_B1': ('0169', 'VVT Bank 1', '°', 360),
                'VVT_B2': ('016B', 'VVT Bank 2', '°', 360),
                'VVT_TARGET_B1': ('016C', 'VVT Hedef B1', '°', 360),
                'VVT_TARGET_B2': ('016E', 'VVT Hedef B2', '°', 360)
            },
            'AKUMULATOR': {
                'VOLTAGE': ('0142', 'Akü Voltajı', 'V', 20),
                'ALTERNATOR': ('0143', 'Alternatör', 'V', 20),
                'LOAD_PCT': ('0144', 'Yük Yüzdesi', '%', 100),
                'HYBRID_BATTERY': ('015B', 'Hibrit Akü', '%', 100)
            }
        }
        
        # Tüm PID'leri düz liste haline getir
        self.pid_commands = {}
        for category in self.pid_categories.values():
            self.pid_commands.update(category)
        
    def set_terminal(self, terminal):
        self.terminal = terminal
    
    def _log(self, message, message_type="info"):
        if self.terminal:
            self.terminal.append_message(message, message_type)
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            self.socket.settimeout(5.0)
            
            # Initialize ELM327
            self._log("ELM327 başlatılıyor...", "info")
            
            # Reset
            self._log("Reset gönderiliyor...", "info")
            self._send_command("ATZ")
            time.sleep(2)
            
            # Echo off
            self._log("Echo kapatılıyor...", "info")
            self._send_command("ATE0")
            
            # Diğer ayarlar
            self._log("Protokol ayarları yapılıyor...", "info")
            self._send_command("ATL0")   # Linefeeds off
            self._send_command("ATH0")   # Headers off
            self._send_command("ATS0")   # Spaces off
            self._send_command("ATSP0")  # Auto protocol
            
            # Desteklenen PID'leri kontrol et
            self._log("PID desteği kontrol ediliyor...", "info")
            response = self._send_command("0100")
            if response and "NO DATA" not in response:
                self._log("PID Desteği: OK", "info")
            else:
                self._log("PID desteği alınamadı!", "warning")
            
            self.connected = True
            self._log("Bağlantı başarılı", "info")
            return True, "Bağlantı başarılı"
            
        except Exception as e:
            self.connected = False
            error_msg = f"Bağlantı hatası: {str(e)}"
            self._log(error_msg, "error")
            return False, error_msg
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.connected = False
            self._log("Bağlantı kapatıldı", "info")
    
    def _send_command(self, command, retries=3):
        if not self.socket:
            self._log("Bağlantı yok!", "error")
            return None
        
        for attempt in range(retries):
            try:
                # Komutu gönder
                self._log(f"TX: {command}", "tx")
                self.socket.send((command + "\r").encode())
                
                # Yanıtı al
                response = self.socket.recv(1024).decode().strip()
                self._log(f"RX: {response}", "rx")
                
                if "ERROR" in response or "UNABLE TO CONNECT" in response:
                    if attempt == retries - 1:
                        self._log(f"Komut hatası: {response}", "error")
                    time.sleep(0.5)
                    continue
                    
                return response
                
            except socket.timeout:
                if attempt == retries - 1:
                    self._log(f"Timeout hatası (Deneme {attempt + 1}/{retries})", "error")
                time.sleep(0.5)
                continue
            except Exception as e:
                self._log(f"Komut gönderme hatası: {str(e)}", "error")
                return None
                
        return None

    def parse_response(self, pid, response):
        try:
            if not response or "NO DATA" in response:
                return None
                
            data = response.split('\r')[-1]
            data = ''.join(c for c in data if c.isalnum())
            
            if len(data) < 4:
                return None
            
            # A ve B değerlerini al
            if len(data) >= 8:
                A = int(data[4:6], 16)
                B = int(data[6:8], 16)
            else:
                A = int(data[4:6], 16)
                B = 0
            
            # PID'e göre formül uygula
            if pid == 'RPM':  # 010C
                return ((A * 256) + B) / 4
            elif pid in ['SPEED', 'LOAD', 'THROTTLE', 'EGR', 'FUEL_LEVEL']:
                return A * 100.0 / 255.0
            elif pid in ['COOLANT_TEMP', 'INTAKE_TEMP', 'OIL_TEMP', 'AMBIENT_TEMP']:
                return A - 40
            elif pid == 'FUEL_PRESSURE':  # 010A
                return A * 3
            elif pid == 'MAP':  # 010B
                return A
            elif pid == 'TIMING_ADV':  # 010E
                return (A - 128) / 2
            elif pid == 'MAF':  # 0110
                return ((A * 256.0) + B) / 100
            elif pid == 'O2_VOLTAGE':  # 0114
                return A / 200
            elif pid == 'RUNTIME':  # 011F
                return (A * 256.0) + B
            elif pid == 'FUEL_RATE':  # 015E
                return ((A * 256.0) + B) / 20
            elif pid == 'CATALYST_TEMP':  # 013C
                return ((A * 256.0) + B) / 10 - 40
            elif pid == 'EVAP':  # 0132
                return ((A * 256.0) + B) * 0.25
            elif pid in ['VOLTAGE', 'ALTERNATOR']:
                return ((A * 256.0) + B) / 1000
            
            return None
                
        except Exception:
            return None

    def read_all_data(self):
        data = {'timestamp': datetime.now().isoformat()}
        
        for pid_name in self.pid_commands:
            response = self._send_command(self.pid_commands[pid_name][0])
            value = self.parse_response(pid_name, response)
            data[pid_name] = value
            time.sleep(0.1)
            
        return data

    def set_protocol(self, protocol_name):
        if protocol_name in OBD_PROTOCOLS:
            command, _ = OBD_PROTOCOLS[protocol_name]
            self._log(f"Protokol değiştiriliyor: {protocol_name}", "info")
            response = self._send_command(command)
            time.sleep(1)
            
            # Protokol değişikliğini kontrol et
            self._send_command("ATDP")
            self.current_protocol = protocol_name
            return True
        return False
    
    def get_current_protocol(self):
        response = self._send_command("ATDP")
        self._log(f"Aktif Protokol: {response}", "info")
        return response

class OBD2GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        
        self.obd = OBD2Connection()
        self.reader_thread = None
        self.scanner_thread = None
        self.recording = False
        self.csv_file = None
        self.csv_writer = None
        
        # GUI güncellemeleri için timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gui)
        self.update_timer.setInterval(100)  # 100ms
        
        # Veri tamponu
        self.data_buffer = None
        self.data_mutex = QMutex()
        
        self.init_ui()
        self.obd.set_terminal(self.terminal)
    
    def init_ui(self):
        self.setWindowTitle('OBD2 Veri Okuyucu')
        self.setGeometry(100, 100, 1200, 800)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Dikey splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Üst kısım (mevcut arayüz)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Bağlantı ayarları
        conn_layout = QHBoxLayout()
        self.ip_input = QLineEdit(self.obd.ip)
        self.port_input = QLineEdit(str(self.obd.port))
        self.connect_btn = QPushButton('Bağlan')
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        conn_layout.addWidget(QLabel('IP:'))
        conn_layout.addWidget(self.ip_input)
        conn_layout.addWidget(QLabel('Port:'))
        conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.connect_btn)
        
        # Bağlantı ayarları satırına protokol seçimi ekle
        self.protocol_combo = QComboBox()
        for protocol_name, (_, description) in OBD_PROTOCOLS.items():
            self.protocol_combo.addItem(description, protocol_name)
        self.protocol_combo.setCurrentText(OBD_PROTOCOLS['AUTO'][1])
        self.protocol_combo.currentIndexChanged.connect(self.protocol_changed)
        
        self.scan_btn = QPushButton('Protokol Tara')
        self.scan_btn.clicked.connect(self.start_protocol_scan)
        self.scan_btn.setEnabled(False)
        
        conn_layout.addWidget(QLabel('Protokol:'))
        conn_layout.addWidget(self.protocol_combo)
        conn_layout.addWidget(self.scan_btn)
        
        top_layout.addLayout(conn_layout)
        
        # Tab widget
        tab_widget = QTabWidget()
        self.value_labels = {}
        self.progress_bars = {}
        
        # Sensör sekmeleri
        for category_name, category_pids in self.obd.pid_categories.items():
            tab = QWidget()
            tab_layout = QGridLayout()
            
            row = 0
            for pid, (_, name, unit, max_value) in category_pids.items():
                # Başlık
                label = QLabel(f"{name}:")
                label.setFont(QFont('Arial', 10, QFont.Bold))
                tab_layout.addWidget(label, row, 0)
                
                # Değer
                value_label = QLabel('--')
                value_label.setFont(QFont('Arial', 12))
                value_label.setMinimumWidth(100)
                tab_layout.addWidget(value_label, row, 1)
                self.value_labels[pid] = value_label
                
                # Birim
                unit_label = QLabel(unit)
                tab_layout.addWidget(unit_label, row, 2)
                
                # Progress bar
                if max_value > 0:  # Sadece anlamlı değerler için progress bar göster
                    pbar = QProgressBar()
                    pbar.setMaximumHeight(15)
                    pbar.setMaximum(int(max_value))
                    tab_layout.addWidget(pbar, row, 3)
                    self.progress_bars[pid] = pbar
                
                row += 1
            
            tab.setLayout(tab_layout)
            tab_widget.addTab(tab, category_name)
        
        # CAN Decoder sekmesi
        can_decoder = CANDecoder()
        tab_widget.addTab(can_decoder, "CAN Decoder")
        
        top_layout.addWidget(tab_widget)
        
        # Kayıt kontrolleri
        record_layout = QHBoxLayout()
        self.record_btn = QPushButton('Kayıt Başlat')
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setEnabled(False)
        record_layout.addWidget(self.record_btn)
        top_layout.addLayout(record_layout)
        
        # Durum çubuğu
        self.status_label = QLabel('Hazır')
        top_layout.addWidget(self.status_label)
        
        splitter.addWidget(top_widget)
        
        # Alt kısım (terminal)
        self.terminal = TerminalWidget()
        splitter.addWidget(self.terminal)
        
        main_layout.addWidget(splitter)
        
        # Splitter oranlarını ayarla
        splitter.setStretchFactor(0, 7)  # Üst kısım
        splitter.setStretchFactor(1, 3)  # Alt kısım (terminal)
        
        self.show()
    
    def update_gui(self):
        with QMutexLocker(self.data_mutex):
            if self.data_buffer is None:
                return
            data = self.data_buffer.copy()
            self.data_buffer = None
        
        # GUI güncellemelerini ana thread'de yap
        self.update_values(data)
    
    def update_values(self, data):
        try:
            for pid in self.obd.pid_commands:
                value = data.get(pid)
                
                if value is not None:
                    # Değer göstergesini güncelle
                    self.value_labels[pid].setText(f"{value:.1f}")
                    
                    # Progress bar'ı güncelle
                    if pid in self.progress_bars:
                        self.progress_bars[pid].setValue(int(value))
                    
                    # Sıcaklık için renk kodlaması
                    if pid in ['COOLANT_TEMP', 'OIL_TEMP']:
                        if value > 100:
                            self.value_labels[pid].setStyleSheet('color: red')
                        elif value > 90:
                            self.value_labels[pid].setStyleSheet('color: orange')
                        else:
                            self.value_labels[pid].setStyleSheet('color: white')
                else:
                    self.value_labels[pid].setText('--')
                    if pid in self.progress_bars:
                        self.progress_bars[pid].setValue(0)
            
            # CSV'ye kaydet
            if self.recording and self.csv_writer:
                self.csv_writer.writerow(data)
                self.csv_file.flush()
                
        except Exception as e:
            self.terminal.append_message(f"GUI güncelleme hatası: {str(e)}", "error")
    
    def on_data_received(self, data):
        with QMutexLocker(self.data_mutex):
            self.data_buffer = data
    
    def toggle_connection(self):
        try:
            if not self.obd.connected:
                self.connect_btn.setEnabled(False)
                self.terminal.append_message("Bağlantı kuruluyor...", "info")
                
                self.obd.ip = self.ip_input.text()
                self.obd.port = int(self.port_input.text())
                success, message = self.obd.connect()
                
                if success:
                    self.connect_btn.setText('Bağlantıyı Kes')
                    self.record_btn.setEnabled(True)
                    self.scan_btn.setEnabled(True)
                    
                    # Okuyucu thread'i başlat
                    self.reader_thread = OBD2Reader(self.obd)
                    self.reader_thread.data_received.connect(self.on_data_received)
                    self.reader_thread.connection_error.connect(self.handle_connection_error)
                    self.reader_thread.start()
                    
                    # GUI güncelleme timer'ını başlat
                    self.update_timer.start()
                
                self.status_label.setText(message)
            else:
                self.update_timer.stop()
                
                if self.reader_thread:
                    self.reader_thread.stop()
                    self.reader_thread.wait()
                    self.reader_thread = None
                
                if self.scanner_thread:
                    self.scanner_thread.stop()
                    self.scanner_thread.wait()
                    self.scanner_thread = None
                
                self.obd.disconnect()
                self.connect_btn.setText('Bağlan')
                self.record_btn.setEnabled(False)
                self.scan_btn.setEnabled(False)
                self.status_label.setText('Bağlantı kesildi')
                
                if self.recording:
                    self.toggle_recording()
        finally:
            self.connect_btn.setEnabled(True)
    
    def handle_connection_error(self, error_msg):
        self.terminal.append_message(f"Bağlantı hatası: {error_msg}", "error")
        self.status_label.setText(f"Bağlantı hatası: {error_msg}")
        self.toggle_connection()
    
    def toggle_recording(self):
        if not self.recording:
            # Kayıt başlat
            try:
                if not os.path.exists('logs'):
                    os.makedirs('logs')
                
                filename = f"logs/obd2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                self.csv_file = open(filename, 'w', newline='')
                self.csv_writer = csv.DictWriter(
                    self.csv_file, 
                    fieldnames=['timestamp'] + list(self.obd.pid_commands.keys())
                )
                self.csv_writer.writeheader()
                
                self.recording = True
                self.record_btn.setText('Kaydı Durdur')
                self.status_label.setText(f'Kayıt başladı: {filename}')
                
            except Exception as e:
                QMessageBox.critical(self, 'Hata', f'Kayıt başlatılamadı: {str(e)}')
                return
        else:
            # Kaydı durdur
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            
            self.recording = False
            self.record_btn.setText('Kayıt Başlat')
            self.status_label.setText('Kayıt durduruldu')
    
    def closeEvent(self, event):
        self.update_timer.stop()
        
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
        
        if self.scanner_thread:
            self.scanner_thread.stop()
            self.scanner_thread.wait()
        
        if self.obd.connected:
            self.obd.disconnect()
        
        if self.recording:
            self.toggle_recording()
        
        event.accept()
    
    def protocol_changed(self, index):
        if self.obd.connected:
            protocol_name = self.protocol_combo.currentData()
            if self.obd.set_protocol(protocol_name):
                self.terminal.append_message(f"Protokol değiştirildi: {protocol_name}", "info")
            else:
                self.terminal.append_message("Protokol değiştirilemedi!", "error")
    
    def start_protocol_scan(self):
        if not self.scanner_thread:
            self.terminal.append_message("Protokol taraması başlatılıyor...", "info")
            self.scan_btn.setText('Taramayı Durdur')
            self.protocol_combo.setEnabled(False)
            
            self.scanner_thread = ProtocolScanner(self.obd)
            self.scanner_thread.protocol_found.connect(self.on_protocol_found)
            self.scanner_thread.scan_complete.connect(self.on_scan_complete)
            self.scanner_thread.start()
        else:
            self.scanner_thread.stop()
            self.scanner_thread.wait()
            self.scanner_thread = None
            self.scan_btn.setText('Protokol Tara')
            self.protocol_combo.setEnabled(True)
            self.terminal.append_message("Protokol taraması durduruldu", "warning")
    
    def on_protocol_found(self, protocol_name, description):
        self.terminal.append_message(f"Desteklenen protokol bulundu: {description}", "info")
        # Bulunan protokole otomatik geç
        index = self.protocol_combo.findData(protocol_name)
        if index >= 0:
            self.protocol_combo.setCurrentIndex(index)
    
    def on_scan_complete(self):
        self.scanner_thread = None
        self.scan_btn.setText('Protokol Tara')
        self.protocol_combo.setEnabled(True)
        self.terminal.append_message("Protokol taraması tamamlandı", "info")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Koyu tema
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    ex = OBD2GUI()
    sys.exit(app.exec_()) 