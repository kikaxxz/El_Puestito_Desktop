import os
import json
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QHeaderView, QTableWidgetItem, QDialog, QMessageBox, QLineEdit,
    QFormLayout, QComboBox, QProgressBar, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from logger_setup import setup_logger

logger = setup_logger()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EmployeeFormDialog(QDialog):
    # [NOTA: Pega aquí EXACTAMENTE la clase EmployeeFormDialog que tenías en admin_page.py]
    # (Omitida por longitud, pero es la misma clase original de tu código)
    pass # <-- Reemplaza este pass con tu código original de EmployeeFormDialog

class EmployeesTab(QWidget):
    def __init__(self, app_controller, config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.employees_data = []
        
        self.available_roles = list(config.get("roles_pago", {}).keys())
        if not self.available_roles:
            self.available_roles = ["Mesero", "Cajera", "Jefe de Cocina", "Michelero"]

        self.setup_ui()
        self.refresh_employee_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        controls_layout = QHBoxLayout()
        self.btn_add = QPushButton("Añadir Empleado")
        self.btn_add.setObjectName("orange_button")
        self.btn_edit = QPushButton("Editar Empleado")
        self.btn_edit.setObjectName("orange_button")
        self.btn_delete = QPushButton("Eliminar Empleado")
        self.btn_delete.setObjectName("orange_button")
        
        self.btn_format_sensor = QPushButton("Formatear Sensor")
        self.btn_format_sensor.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; padding: 5px; border-radius: 5px;")
        self.btn_format_sensor.setFixedWidth(150)

        controls_layout.addWidget(self.btn_add)
        controls_layout.addWidget(self.btn_edit)
        controls_layout.addWidget(self.btn_delete)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_format_sensor)
        layout.addLayout(controls_layout)

        self.employee_table = QTableWidget()
        self.employee_table.setObjectName("employee_table")
        self.employee_table.setColumnCount(3) 
        self.employee_table.setHorizontalHeaderLabels(["ID", "Nombre Completo", "Rol"]) 
        header = self.employee_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.employee_table.setColumnWidth(0, 150)
        self.employee_table.setColumnWidth(2, 150)
        layout.addWidget(self.employee_table)

        self.btn_add.clicked.connect(self.add_employee)
        self.btn_edit.clicked.connect(self.edit_employee)
        self.btn_delete.clicked.connect(self.delete_employee)
        self.btn_format_sensor.clicked.connect(self.formatear_sensor)

    def refresh_employee_table(self):
        self.employees_data = self.app_controller.get_todos_los_empleados()
        self.employee_table.setRowCount(0)
        self.employee_table.setRowCount(len(self.employees_data))
        for row, employee in enumerate(self.employees_data):
            id_item = QTableWidgetItem(employee.get("id_empleado"))
            name_item = QTableWidgetItem(employee.get("nombre"))
            rol_item = QTableWidgetItem(employee.get("rol", "No asignado"))
            
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            rol_item.setFlags(rol_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.employee_table.setItem(row, 0, id_item)
            self.employee_table.setItem(row, 1, name_item)
            self.employee_table.setItem(row, 2, rol_item)

    def add_employee(self):
        dialog = EmployeeFormDialog(self, available_roles=self.available_roles, api_key=self.app_controller.API_KEY, server_url=self.app_controller.SERVER_URL)
        if dialog.exec():
            data = dialog.get_data()
            if not data['id'] or not data['nombre']: return 
            
            if self.app_controller.data_manager.get_employee_by_id(data['id']):
                QMessageBox.warning(self, "Error", f"El ID '{data['id']}' ya existe.")
                return

            result = self.app_controller.agregar_empleado(data['id'], data['nombre'], data['rol'], data['fingerprint_id'])
            if result:
                self.refresh_employee_table()
            else:
                QMessageBox.critical(self, "Error", "No se pudo añadir el empleado.")

    def edit_employee(self):
        current_row = self.employee_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección", "Seleccione un empleado.")
            return
        
        original_id = self.employee_table.item(current_row, 0).text()
        original_employee = self.app_controller.data_manager.get_employee_by_id(original_id)
        
        dialog = EmployeeFormDialog(self, employee_data=original_employee, available_roles=self.available_roles, api_key=self.app_controller.API_KEY, server_url=self.app_controller.SERVER_URL)
        if dialog.exec():
            data = dialog.get_data()
            if data['id'] != original_id and self.app_controller.data_manager.get_employee_by_id(data['id']):
                QMessageBox.warning(self, "Error", f"El ID '{data['id']}' ya existe.")
                return

            self.app_controller.editar_empleado(original_id, data['id'], data['nombre'], data['rol'], data['fingerprint_id'])
            self.refresh_employee_table()

    def delete_employee(self):
        current_row = self.employee_table.currentRow()
        if current_row < 0: return

        employee_id = self.employee_table.item(current_row, 0).text()
        employee_name = self.employee_table.item(current_row, 1).text()
        
        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar a '{employee_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            result = self.app_controller.eliminar_empleado(employee_id)
            if result is None:
                QMessageBox.critical(self, "Error", "No se pudo eliminar.")
                return
            self.refresh_employee_table()

    def formatear_sensor(self):
        confirm = QMessageBox.warning(self, "PELIGRO", "¿Formatear sensor biométrico?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                requests.post(f"{self.app_controller.SERVER_URL}/api/biometric/start-clear", headers={'X-API-KEY': self.app_controller.API_KEY}, timeout=5)
                QMessageBox.information(self, "Enviado", "Formateando...")
            except Exception as e:
                logger.error(str(e))