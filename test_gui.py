import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Test Uygulaması')
        self.setGeometry(100, 100, 400, 200)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test butonu
        self.test_btn = QPushButton('Test Et')
        self.test_btn.clicked.connect(self.on_test)
        layout.addWidget(self.test_btn)
        
        # Durum etiketi
        self.status_label = QLabel('Hazır')
        layout.addWidget(self.status_label)
        
        self.show()
    
    def on_test(self):
        self.status_label.setText('Test başarılı!')

if __name__ == '__main__':
    # X11 kullanımını zorla
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    
    app = QApplication(sys.argv)
    ex = TestWindow()
    sys.exit(app.exec_()) 