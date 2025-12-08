from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt

class PinDialog(QDialog):
    def __init__(self, correct_pin, role_name, parent=None):
        super().__init__(parent)
        self.correct_pin = correct_pin
        self.current_pin = ""
        
        self.setWindowTitle(f"Acceso - {role_name}")
        self.setFixedSize(320, 450)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setObjectName("pin_container")
        container.setStyleSheet("""
            QWidget#pin_container {
                background-color: rgba(30, 31, 35, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
            QLabel { color: white; font-weight: bold; }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 35px; /* Redondos */
                font-size: 24px;
                color: white;
            }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.15); }
            QPushButton#btn_clear { color: #ff4757; font-size: 18px; font-weight: bold; }
            QPushButton#btn_enter { color: #00d26a; }
            QPushButton#btn_close { 
                background-color: transparent; color: #888; font-size: 14px; border-radius: 0;
            }
            QPushButton#btn_close:hover { color: white; }
        """)
        
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(20, 20, 20, 20)
        inner_layout.setSpacing(15)
        
        btn_close = QPushButton("Cancelar")
        btn_close.setObjectName("btn_close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        inner_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        lbl_title = QLabel(f"Ingrese PIN para\n{role_name}")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-size: 18px; margin-bottom: 10px;")
        inner_layout.addWidget(lbl_title)
        
        self.lbl_display = QLabel("----")
        self.lbl_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_display.setStyleSheet("font-size: 32px; letter-spacing: 5px; color: #f76606; margin-bottom: 20px;")
        inner_layout.addWidget(self.lbl_display)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('✕', 3, 0), ('0', 3, 1), ('➜', 3, 2),
        ]
        
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(70, 70)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if text == '✕':
                btn.setObjectName("btn_clear")
                btn.clicked.connect(self.clear_pin)
            elif text == '➜':
                btn.setObjectName("btn_enter")
                btn.clicked.connect(self.verify_pin)
            else:
                btn.clicked.connect(lambda _, t=text: self.add_digit(t))
                
            grid_layout.addWidget(btn, row, col)
            
        inner_layout.addLayout(grid_layout)
        main_layout.addWidget(container)

    def add_digit(self, digit):
        if len(self.current_pin) < 4:
            self.current_pin += digit
            self.update_display()
            
    def clear_pin(self):
        self.current_pin = ""
        self.update_display()
        
    def update_display(self):
        masked = "*" * len(self.current_pin)
        padded = masked.ljust(4, '-')
        self.lbl_display.setText(padded)
        
    def verify_pin(self):
        if len(self.current_pin) != 4:
            return 
            
        if self.current_pin == self.correct_pin:
            self.accept()
        else:
            self.lbl_display.setStyleSheet("font-size: 32px; letter-spacing: 5px; color: #ff4757; margin-bottom: 20px;")
            self.lbl_display.setText("ERROR")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self.reset_style_after_error)

    def reset_style_after_error(self):
        self.current_pin = ""
        self.lbl_display.setStyleSheet("font-size: 32px; letter-spacing: 5px; color: #f76606; margin-bottom: 20px;")
        self.update_display()