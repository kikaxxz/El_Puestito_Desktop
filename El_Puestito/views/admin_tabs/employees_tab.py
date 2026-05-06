import os
import json
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
    def __init__(self, parent=None, employee_data=None, available_roles=None, api_key=None, server_url=None):
        super().__init__(parent)
        self.setWindowTitle("Empleado")
        self.setModal(True)
        self.setMinimumWidth(350)
        self.available_roles = available_roles if available_roles else []
        self.employee_data = employee_data
        self.api_key = api_key
        self.server_url = server_url
        self.setup_ui()
        self.populate_data()
        self.validate_form()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_input = QLineEdit()
        self.id_input.textChanged.connect(self.validate_form)

        self.nombre_input = QLineEdit()
        self.nombre_input.textChanged.connect(self.validate_form)

        self.rol_combo = QComboBox()
        self.rol_combo.addItems(self.available_roles)

        self.fingerprint_input = QLineEdit()
        self.fingerprint_input.setPlaceholderText("Opcional")

        form_layout.addRow("ID:", self.id_input)
        form_layout.addRow("Nombre Completo:", self.nombre_input)
        form_layout.addRow("Rol:", self.rol_combo)
        form_layout.addRow("ID Huella:", self.fingerprint_input)

        layout.addLayout(form_layout)

        self.warning_label = QLabel("Los campos ID y Nombre son obligatorios.")
        self.warning_label.setStyleSheet("color: red; font-size: 11px;")
        layout.addWidget(self.warning_label)

        buttons_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_save)
        buttons_layout.addWidget(self.btn_cancel)

        layout.addLayout(buttons_layout)

    def populate_data(self):
        if self.employee_data:
            self.id_input.setText(str(self.employee_data.get("id_empleado", "")))
            self.nombre_input.setText(str(self.employee_data.get("nombre", "")))
            rol = self.employee_data.get("rol", "")
            if rol in self.available_roles:
                self.rol_combo.setCurrentText(rol)
            self.fingerprint_input.setText(str(self.employee_data.get("fingerprint_id", "")))

    def validate_form(self):
        id_text = self.id_input.text().strip()
        nombre_text = self.nombre_input.text().strip()
        is_valid = bool(id_text) and bool(nombre_text)
        
        error_style = "border: 1px solid red;"
        normal_style = ""

        if not id_text:
            self.id_input.setStyleSheet(error_style)
        else:
            self.id_input.setStyleSheet(normal_style)

        if not nombre_text:
            self.nombre_input.setStyleSheet(error_style)
        else:
            self.nombre_input.setStyleSheet(normal_style)

        self.btn_save.setEnabled(is_valid)
        self.warning_label.setVisible(not is_valid)

    def get_data(self):
        return {
            "id": self.id_input.text().strip(),
            "nombre": self.nombre_input.text().strip(),
            "rol": self.rol_combo.currentText(),
            "fingerprint_id": self.fingerprint_input.text().strip() or None
        }

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
            self.app_controller.formatear_sensor_biometrico()
            QMessageBox.information(self, "Enviado", "La orden de formateo ha sido enviada al servidor de forma asíncrona.")