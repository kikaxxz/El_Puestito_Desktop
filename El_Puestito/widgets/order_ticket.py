import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class OrderTicket(QFrame):
    def __init__(self, orden_data, parent=None):
        super().__init__(parent)
        self.setObjectName("order_ticket")
        self.setFixedWidth(300)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        mesa_str = str(orden_data.get('numero_mesa', '?'))
        mesa_label = QLabel(f"Mesa {mesa_str}")
        mesa_label.setObjectName("ticket_header")
        mesa_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mesa_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(mesa_label)
        main_layout.addLayout(header_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #ccc;")
        main_layout.addWidget(line)
        
        items_container = QWidget()
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(0, 0, 0, 0)
        items_layout.setSpacing(8)
        
        for item in orden_data.get('items', []):
            self._add_item_row(items_layout, item)
            
        main_layout.addWidget(items_container)
        main_layout.addStretch()
        
        self.btn_listo = QPushButton("Marcar Listo")
        self.btn_listo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_listo.setObjectName("btn_listo")
        self.btn_listo.setFixedHeight(40)
        self.btn_listo.setStyleSheet("""
            QPushButton {
                background-color: #28a745; 
                color: white; 
                font-weight: bold; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        main_layout.addWidget(self.btn_listo)

    def _add_item_row(self, layout, item):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        
        img_label = QLabel()
        img_label.setFixedSize(50, 50)
        img_label.setStyleSheet("background-color: #eee; border-radius: 5px; border: 1px solid #ddd;")
        img_name = item.get("imagen")
        
        if img_name:
            img_path = os.path.join(BASE_DIR, "assets", img_name)
            if os.path.exists(img_path):
                pix = QPixmap(img_path)
                img_label.setPixmap(pix.scaled(
                    50, 50, 
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                    Qt.TransformationMode.SmoothTransformation
                ))
        row_layout.addWidget(img_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        qty = item.get('cantidad', 1)
        name = item.get('nombre', 'Item')
        
        title = QLabel(f"{qty}x  {name}")
        title.setObjectName("ticket_item_name")
        title.setWordWrap(True)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(title)
        
        notas = item.get('notas', '')
        if notas:
            lbl_notas = QLabel(f"{notas}")
            lbl_notas.setObjectName("ticket_item_notes")
            lbl_notas.setWordWrap(True)
            lbl_notas.setStyleSheet("color: #d9534f; font-style: italic; font-size: 12px;")
            info_layout.addWidget(lbl_notas)
            
        row_layout.addLayout(info_layout)
        layout.addWidget(row_widget)