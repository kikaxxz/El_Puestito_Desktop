import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class OrderTicket(QFrame):
    item_marcado_listo = pyqtSignal(int)

    def __init__(self, orden_data, parent=None):
        super().__init__(parent)
        self.datos = orden_data 
        self.setObjectName("order_ticket")
        self.setFixedWidth(300)
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame#order_ticket {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 10px;
            }
            QLabel { color: white; }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        
        self.mesa_label = QLabel()
        self.mesa_label.setObjectName("ticket_header")
        self.mesa_label.setStyleSheet("font-size: 20px; font-weight: 900; color: #ffffff;")
        
        header_layout.addWidget(self.mesa_label)
        header_layout.addStretch()
        
        self.time_label = QLabel()
        self.time_label.setStyleSheet("background-color: #444; padding: 4px 8px; border-radius: 5px; font-weight: bold;")
        header_layout.addWidget(self.time_label)

        main_layout.addLayout(header_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #555; max-height: 1px;")
        main_layout.addWidget(line)
        
        items_container = QWidget()
        self.items_layout = QVBoxLayout(items_container)
        self.items_layout.setContentsMargins(0, 5, 0, 5)
        self.items_layout.setSpacing(12) 
        
        main_layout.addWidget(items_container)
        main_layout.addStretch()
        
        self.btn_listo = QPushButton("MARCAR LISTO")
        self.btn_listo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_listo.setObjectName("btn_listo")
        self.btn_listo.setFixedHeight(45)
        self.btn_listo.setStyleSheet("""
            QPushButton {
                background-color: #00d26a; 
                color: black; 
                font-weight: 800; 
                font-size: 14px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #00e676;
            }
            QPushButton:pressed {
                background-color: #00a352;
            }
        """)
        main_layout.addWidget(self.btn_listo)

        self.update_data(self.datos)

    def update_data(self, nueva_orden_data):
        self.datos = nueva_orden_data
        mesa_str = str(self.datos.get('numero_mesa', '?'))
        self.mesa_label.setText(f"Mesa {mesa_str}")

        if 'fecha_apertura' in self.datos:
            try:
                hora = self.datos['fecha_apertura'].split('T')[1][:5]
                self.time_label.setText(hora)
                self.time_label.show()
            except Exception:
                self.time_label.hide()
        else:
            self.time_label.hide()

        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for item in self.datos.get('items', []):
            self._add_item_row(self.items_layout, item)

    def _add_item_row(self, layout, item):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)
        
        img_label = QLabel()
        img_label.setFixedSize(50, 50)
        img_label.setStyleSheet("background-color: #333; border-radius: 8px;")
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        img_name = item.get("imagen")
        pix_loaded = False
        
        if img_name:
            img_path = os.path.join(BASE_DIR, "assets", img_name)
            if os.path.exists(img_path):
                pix = QPixmap(img_path)
                img_label.setPixmap(pix.scaled(
                    50, 50, 
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                    Qt.TransformationMode.SmoothTransformation
                ))
                pix_loaded = True
        
        if not pix_loaded:
            img_label.setText("IMG") 
            
        row_layout.addWidget(img_label)
        
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        qty = item.get('cantidad', 1)
        name = item.get('nombre', 'Item')
        
        title = QLabel(f"{qty}x  {name}")
        title.setWordWrap(True)
        title.setStyleSheet("font-weight: bold; font-size: 15px; color: #fff;")
        info_layout.addWidget(title)
        
        cerveza = item.get('nombre_cerveza')
        if cerveza:
            lbl_cerveza = QLabel(f"└ Cerveza: {cerveza}")
            lbl_cerveza.setWordWrap(True)
            lbl_cerveza.setStyleSheet("color: #00d26a; font-weight: bold; font-size: 13px; margin-left: 10px;")
            info_layout.addWidget(lbl_cerveza)
        
        nota = item.get('notas', '')
        if nota:
            lbl_nota = QLabel(nota)
            lbl_nota.setWordWrap(True)
            lbl_nota.setStyleSheet("color: #ff9800; font-weight: bold; font-style: italic; font-size: 13px; margin-top: 2px;")
            info_layout.addWidget(lbl_nota)
            
        row_layout.addWidget(info_container)

        btn_indiv = QPushButton("✓")
        btn_indiv.setFixedSize(35, 35)
        btn_indiv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_indiv.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #00d26a;
                font-weight: bold;
                font-size: 18px;
                border-radius: 5px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background-color: #444;
                border: 1px solid #00d26a;
            }
            QPushButton:pressed {
                background-color: #00d26a;
                color: black;
            }
        """)
        
        id_detalle = item.get('id_detalle', -1)
        btn_indiv.clicked.connect(lambda checked, id_d=id_detalle: self.item_marcado_listo.emit(id_d))
        
        row_layout.addWidget(btn_indiv)
        
        layout.addWidget(row_widget)