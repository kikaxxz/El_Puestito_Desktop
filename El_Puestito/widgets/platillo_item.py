import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QPoint

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
        
        imagen_path = os.path.join(BASE_DIR, "assets", item_data.get("imagen", "default.png"))
        pixmap = QPixmap(imagen_path)
        self.image_label.setPixmap(pixmap.scaled(50, 50, 
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        layout.addWidget(self.image_label)
        
        self.text_label = QLabel(item_data.get("nombre", "N/A"))
        self.text_label.setObjectName("menu_item_label")
        
        layout.addWidget(self.text_label)
        layout.addStretch() 
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.actualizarApariencia() 
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def actualizarApariencia(self):
        """Ajusta la opacidad basado en el estado 'disponible'."""
        if self.disponible:
            self.opacity_effect.setOpacity(1.0)
            self.text_label.setStyleSheet("text-decoration: none;")
        else:
            self.opacity_effect.setOpacity(0.4)
            self.text_label.setStyleSheet("text-decoration: line-through;") 

    def mousePressEvent(self, event):
        """Al hacer clic, cambia el estado y actualiza la apariencia."""
        self.disponible = not self.disponible
        self.actualizarApariencia()
        print(f"Item {self.item_id} marcado como: {'Disponible' if self.disponible else 'Agotado'}")
        super().mousePressEvent(event)