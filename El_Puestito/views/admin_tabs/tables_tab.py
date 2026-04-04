import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QGridLayout, QSizePolicy, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from widgets.table_card_widget import TableCardWidget
from logger_setup import setup_logger

logger = setup_logger()

class TablesTab(QWidget):
    config_updated = pyqtSignal(dict)

    def __init__(self, app_controller, config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.current_config = config
        self.setup_ui()
        self.populate_table_cards()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Gestionar Mesas:"))
        self.btn_add_table = QPushButton("(+) Añadir Mesa")
        self.btn_add_table.setObjectName("orange_button")
        self.btn_remove_table = QPushButton("(-) Quitar Mesa")
        self.btn_remove_table.setObjectName("orange_button")
        controls_layout.addWidget(self.btn_add_table)
        controls_layout.addWidget(self.btn_remove_table)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        scroll_area_tables = QScrollArea()
        scroll_area_tables.setWidgetResizable(True)
        layout.addWidget(scroll_area_tables)
        self.table_cards_container = QWidget()
        self.table_cards_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_grid_layout = QGridLayout(self.table_cards_container)
        self.table_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.table_grid_layout.setSpacing(20)
        for col in range(5):
            self.table_grid_layout.setColumnStretch(col, 1)
        scroll_area_tables.setWidget(self.table_cards_container)
        self.btn_add_table.clicked.connect(self.add_table)
        self.btn_remove_table.clicked.connect(self.remove_table)

    def populate_table_cards(self):
        while self.table_grid_layout.count():
            item = self.table_grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        total_mesas = self.current_config.get("total_mesas", 10)
        for i in range(total_mesas):
            card = TableCardWidget(i + 1)
            self.table_grid_layout.addWidget(card, i // 5, i % 5)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_grid_layout.addWidget(spacer, self.table_grid_layout.rowCount(), 0, 1, -1)
        self.btn_remove_table.setEnabled(total_mesas > 1)

    def add_table(self):
        current_total = self.current_config.get("total_mesas", 10)
        if current_total < 100:
            self.current_config["total_mesas"] = current_total + 1
            self.populate_table_cards()
            self.app_controller.save_config_to_file(self.current_config)
            self.app_controller.notify_server_config_change()
            self.config_updated.emit(self.current_config)
            logger.info(f"Mesa añadida. Total: {self.current_config['total_mesas']}")
        else:
            QMessageBox.information(self, "Limite Alcanzado", "Se ha alcanzado el numero maximo de mesas (100).")

    def remove_table(self):
        current_total = self.current_config.get("total_mesas", 10)
        if current_total > 1:
            self.current_config["total_mesas"] = current_total - 1
            self.populate_table_cards()
            self.app_controller.save_config_to_file(self.current_config)
            self.app_controller.notify_server_config_change()
            self.config_updated.emit(self.current_config)
            logger.info(f"Mesa eliminada. Total: {self.current_config['total_mesas']}")
        else:
            QMessageBox.warning(self, "Accion no permitida", "Debe haber al menos una mesa.")