from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt

class TableCardWidget(QFrame):

    def __init__(self, table_number, parent=None):
        super().__init__(parent)
        self.setObjectName("table_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 100)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        number_label = QLabel(str(table_number))
        number_label.setObjectName("table_card_number")
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(number_label)