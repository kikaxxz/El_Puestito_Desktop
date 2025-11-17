from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QPoint

class ToggleSwitch(QCheckBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(60, 28) 
        self.setObjectName("toggle_switch")

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)