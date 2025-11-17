from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

class RoleCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon_path, title, role_name, parent=None):
        super().__init__(parent)
        self.setObjectName("role_card")
        self.setFixedSize(180, 180)
        self.role_name = role_name
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        icon_label = QLabel()
        icon_pixmap = QPixmap(icon_path).scaled(64, 64, 
                                                Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setObjectName("role_card_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)