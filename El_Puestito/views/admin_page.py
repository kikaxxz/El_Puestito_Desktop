import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget
from PyQt6.QtCore import pyqtSignal

from views.admin_tabs.employees_tab import EmployeesTab
from views.admin_tabs.tables_tab import TablesTab
from views.admin_tabs.menu_tab import MenuTab
from views.admin_tabs.promos_tab import ComboBuilderTab
from views.admin_tabs.reports_tab import ReportsTab
from views.admin_tabs.payroll_tab import PayrollTab
from views.admin_tabs.printer_tab import PrinterTab

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

        title = QLabel("Panel de Administracion")
        title.setObjectName("section_title")
        main_layout.addWidget(title)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.tab_employees = EmployeesTab(self.app_controller, self.current_config)
        self.tab_widget.addTab(self.tab_employees, "Empleados")

        self.tab_tables = TablesTab(self.app_controller, self.current_config)
        self.tab_tables.config_updated.connect(self.emit_config_update)
        self.tab_widget.addTab(self.tab_tables, "Mesas")

        self.tab_menu = MenuTab(self.app_controller)
        self.tab_widget.addTab(self.tab_menu, "Gestion de Menu")

        self.tab_promos = ComboBuilderTab(self.app_controller)
        self.tab_promos.combo_creado.connect(self.tab_menu.load_menu_data)
        self.tab_widget.addTab(self.tab_promos, "Crear Promociones")

        self.tab_reports = ReportsTab(self.app_controller)
        self.tab_widget.addTab(self.tab_reports, "Reportes")

        self.tab_payroll = PayrollTab(self.app_controller, self.current_config)
        self.tab_widget.addTab(self.tab_payroll, "Nomina")

        self.tab_printer = PrinterTab(self.app_controller, self.current_config)
        self.tab_widget.addTab(self.tab_printer, "Impresora")

    def emit_config_update(self, new_config):
        self.current_config = new_config
        self.config_updated.emit(self.current_config)