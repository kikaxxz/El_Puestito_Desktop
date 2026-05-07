import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QPoint
from logger_setup import setup_logger
from path_manager import get_asset_path

logger = setup_logger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class PlatilloItemWidget(QWidget):

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.item_id = item_data.get("id")
        self.disponible = item_data.get("disponible", True) 
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(15)
        
        self.image_label = QLabel()
        self.image_label.setFixedSize(50, 50) 
        self.image_label.setObjectName("menu_item_image")
        
        imagen_nombre = item_data.get("imagen", "default.png")
        if not imagen_nombre:
            imagen_nombre = "default.png"
            
        imagen_path = get_asset_path(imagen_nombre)
        
        if os.path.exists(imagen_path):
            pixmap = QPixmap(imagen_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(
                    50, 50, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                ))
        else:
            self.image_label.setText("N/A")
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_label.setStyleSheet("background-color: #444; border-radius: 5px; color: #fff; font-size: 12px; font-weight: bold;")
        
        layout.addWidget(self.image_label)
        
        self.text_label = QLabel(item_data.get("nombre", "Desconocido"))
        self.text_label.setObjectName("menu_item_label")
        
        layout.addWidget(self.text_label)
        layout.addStretch() 
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.actualizarApariencia() 
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def actualizarApariencia(self):
        if self.disponible:
            self.opacity_effect.setOpacity(1.0)
            self.text_label.setStyleSheet("text-decoration: none;")
        else:
            self.opacity_effect.setOpacity(0.4)
            self.text_label.setStyleSheet("text-decoration: line-through;") 

    def mousePressEvent(self, event):
        self.disponible = not self.disponible
        self.actualizarApariencia()
        logger.info(f"Item {self.item_id} marcado como: {'Disponible' if self.disponible else 'Agotado'}")
        super().mousePressEvent(event)