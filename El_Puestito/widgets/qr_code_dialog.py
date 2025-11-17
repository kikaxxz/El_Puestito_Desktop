import os
import io
import socket
import qrcode
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class QRCodeDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ordenes_activas = {}
        self.ventas_file_path = os.path.join(BASE_DIR, "assets", "ventas_completadas.json")
        
        self.setWindowTitle("Conexión del Servidor")
        self.setFixedSize(300, 350)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        instruction_label = QLabel("Escanea este código desde la app del teléfono:")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(250, 250)
        
        layout.addWidget(instruction_label)
        layout.addWidget(self.qr_label)
        
        self.generate_and_display_qr()

    def get_local_ip(self):
        """Encuentra la dirección IP local de la computadora."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
    
    def generate_and_display_qr(self):
        ip_address = self.get_local_ip()
        server_url = f"http://{ip_address}:5000"
        
        print(f"🖥️  Generando QR para la dirección: {server_url}")
        qr_image = qrcode.make(server_url)
        
        buffer = io.BytesIO()
        qr_image.save(buffer, "PNG")
        buffer.seek(0)
        
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        self.qr_label.setPixmap(pixmap.scaled(250, 250))