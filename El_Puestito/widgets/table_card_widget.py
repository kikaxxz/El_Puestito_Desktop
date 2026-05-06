from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt

class TableCardWidget(QFrame):

    def __init__(self, table_number: int, parent=None):
        super().__init__(parent)
        self.setObjectName("table_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 100)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.number_label = QLabel(str(table_number))
        self.number_label.setObjectName("table_card_number")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.number_label)
        self.set_status(False)

    def update_table_number(self, new_number: int):
        self.number_label.setText(str(new_number))

    def set_status(self, is_occupied: bool):
        if is_occupied:
            self.setStyleSheet("""
                QFrame#table_card {
                    background-color: #5c1a1a;
                    border: 2px solid #D32F2F;
                    border-radius: 10px;
                }
                QLabel#table_card_number {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 20px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#table_card {
                    background-color: #2b2b2b;
                    border: 1px solid #3d3d3d;
                    border-radius: 10px;
                }
                QLabel#table_card_number {
                    color: #aaaaaa;
                    font-weight: bold;
                    font-size: 20px;
                }
            """)