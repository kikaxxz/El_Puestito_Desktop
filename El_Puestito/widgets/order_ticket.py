import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class OrderTicketWidget(QFrame):
    orden_lista = pyqtSignal(QWidget)

    def __init__(self, orden_data, parent=None):
        super().__init__(parent)
        self.setObjectName("order_ticket")
        self.setFixedWidth(300)
        self.ticket_widget = self 
        
        layout = QVBoxLayout(self)
        
        mesa_label = QLabel(f"Mesa: {orden_data['numero_mesa']}")
        mesa_label.setObjectName("ticket_title")
        layout.addWidget(mesa_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        for item in orden_data['items']:
            item_layout = QHBoxLayout()
            img_label = QLabel()
            img_label.setFixedSize(64, 64)
            imagen_nombre = item.get("imagen", "")
            if imagen_nombre:
                imagen_path = os.path.join(BASE_DIR, "assets", imagen_nombre)
                pixmap = QPixmap(imagen_path)
                img_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            item_layout.addWidget(img_label)
            
            text_layout = QVBoxLayout()
            cantidad = item['cantidad']
            nombre = item['nombre']
            notas = f"({item['notas']})" if item['notas'] else ""
            
            nombre_label = QLabel(f"{cantidad}x {nombre}")
            nombre_label.setObjectName("ticket_item_title")
            nombre_label.setWordWrap(True)
            
            notas_label = QLabel(notas)
            notas_label.setObjectName("ticket_item_notes")
            notas_label.setWordWrap(True)
            
            text_layout.addWidget(nombre_label)
            if notas:
                text_layout.addWidget(notas_label)
            
            item_layout.addLayout(text_layout)
            layout.addLayout(item_layout)
            
        listo_button = QPushButton("Listo")
        listo_button.setObjectName("orange_button")
        listo_button.clicked.connect(self.marcar_como_lista)
        layout.addWidget(listo_button)

    def marcar_como_lista(self):
        """ Emite la señal con una referencia a este mismo widget para que pueda ser eliminado """
        self.orden_lista.emit(self.ticket_widget)