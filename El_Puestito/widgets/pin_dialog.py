from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, QLabel, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer

class PinDialog(QDialog):
    def __init__(self, correct_pin, role_name, parent=None):
        super().__init__(parent)
        self.correct_pin = correct_pin
        self.current_pin = ""
        self.max_length = 4
        self.failed_attempts = 0
        self.max_attempts = 5
        
        self.setFixedSize(280, 400)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setObjectName("pin_container")
        container.setStyleSheet("""
            QWidget#pin_container {
                background-color: #1c1c1e;
                border: 1px solid #333;
                border-radius: 25px;
            }
            QLabel#title_label { 
                color: #8e8e93; 
                font-size: 14px; 
                font-weight: bold;
                text-transform: uppercase;
            }
            QLabel#display_label { 
                font-size: 24px; 
                color: #ffffff;
                letter-spacing: 10px;
            }
            QPushButton {
                background-color: #2c2c2e;
                border: none;
                border-radius: 27px;
                font-size: 20px;
                color: white;
            }
            QPushButton:pressed { 
                background-color: #3a3a3c; 
            }
            QPushButton#btn_clear { 
                background-color: transparent;
                color: #ff453a; 
                font-size: 16px; 
            }
            QPushButton#btn_enter { 
                background-color: transparent;
                color: #32d74b; 
            }
            QPushButton#btn_close { 
                background-color: transparent; 
                color: #636366; 
                font-size: 12px;
            }
        """)
        
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(20, 15, 20, 25)
        inner_layout.setSpacing(10)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("btn_close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        inner_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
        lbl_title = QLabel(f"Acceso {role_name}")
        lbl_title.setObjectName("title_label")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(lbl_title)
        
        self.lbl_display = QLabel("")
        self.lbl_display.setObjectName("display_label")
        self.lbl_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_display()
        inner_layout.addWidget(self.lbl_display)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(12)
        grid_layout.setContentsMargins(5, 5, 5, 5)
        
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('✕', 3, 0), ('0', 3, 1), ('➜', 3, 2),
        ]
        
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(55, 55)
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
        if len(self.current_pin) < self.max_length:
            self.current_pin += digit
            self.update_display()
            if len(self.current_pin) == self.max_length:
                QTimer.singleShot(150, self.verify_pin)
            
    def clear_pin(self):
        self.current_pin = ""
        self.update_display()
        
    def update_display(self):
        dots = "●" * len(self.current_pin)
        empty = "○" * (self.max_length - len(self.current_pin))
        self.lbl_display.setText(dots + empty)
        
    def verify_pin(self):
        if len(self.current_pin) != self.max_length:
            return 
            
        if self.current_pin == str(self.correct_pin):
            self.accept()
        else:
            self.failed_attempts += 1
            self.lbl_display.setStyleSheet("color: #ff453a; font-size: 24px; letter-spacing: 10px;")
            
            if self.failed_attempts >= self.max_attempts:
                QTimer.singleShot(500, self.reject)
            else:
                QTimer.singleShot(500, self.reset_style_after_error)

    def reset_style_after_error(self):
        self.current_pin = ""
        self.lbl_display.setStyleSheet("color: #ffffff; font-size: 24px; letter-spacing: 10px;")
        self.update_display()