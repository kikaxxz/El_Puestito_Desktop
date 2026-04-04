import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget
from PyQt6.QtCore import pyqtSignal

# Importamos las pestañas modulares (las crearemos en el siguiente paso)
from views.admin_tabs.employees_tab import EmployeesTab
from views.admin_tabs.tables_tab import TablesTab
from views.admin_tabs.menu_tab import MenuTab
from views.admin_tabs.promos_tab import ComboBuilderTab
from views.admin_tabs.reports_tab import ReportsTab
from views.admin_tabs.payroll_tab import PayrollTab

from logger_setup import setup_logger
logger = setup_logger()

class AdminPage(QWidget):
    config_updated = pyqtSignal(dict)

    def __init__(self, app_controller, initial_config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller 
        self.current_config = initial_config

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 25)
        main_layout.setSpacing(15)

        title = QLabel("Panel de Administración")
        title.setObjectName("section_title")
        main_layout.addWidget(title)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 1. Pestaña de Empleados
        self.tab_employees = EmployeesTab(self.app_controller, self.current_config)
        self.tab_widget.addTab(self.tab_employees, "Empleados")

        # 2. Pestaña de Mesas
        self.tab_tables = TablesTab(self.app_controller, self.current_config)
        self.tab_tables.config_updated.connect(self.emit_config_update)
        self.tab_widget.addTab(self.tab_tables, "Mesas")

        # 3. Pestaña de Menú
        self.tab_menu = MenuTab(self.app_controller)
        self.tab_widget.addTab(self.tab_menu, "Gestión de Menú")

        # 4. Pestaña de Promociones
        self.tab_promos = ComboBuilderTab(self.app_controller)
        self.tab_promos.combo_creado.connect(self.tab_menu.load_menu_data)
        self.tab_widget.addTab(self.tab_promos, "Crear Promociones")

        # 5. Pestaña de Reportes
        self.tab_reports = ReportsTab(self.app_controller)
        self.tab_widget.addTab(self.tab_reports, "Reportes")

        # 6. Pestaña de Nómina
        self.tab_payroll = PayrollTab(self.app_controller, self.current_config)
        self.tab_widget.addTab(self.tab_payroll, "Nómina")

    def emit_config_update(self, new_config):
        """Propaga el cambio de configuración a MainWindow"""
        self.current_config = new_config
        self.config_updated.emit(self.current_config)