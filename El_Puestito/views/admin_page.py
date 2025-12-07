import os
import json
import datetime
import random
import requests
from fpdf import FPDF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QLineEdit, QFrame, QHeaderView, QTableWidgetItem, QDialog,
    QScrollArea, QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QTabWidget, QGridLayout, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QGraphicsOpacityEffect, QTreeWidgetItemIterator,
    QCalendarWidget, QDateEdit, QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QDate

from widgets.table_card_widget import TableCardWidget
from widgets.platillo_item import PlatilloItemWidget

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def QSpacerItem(arg1, arg2, arg3, arg4):
    raise NotImplementedError

class AdminPage(QWidget):
    config_updated = pyqtSignal(dict)

    def __init__(self, app_controller, initial_config, parent=None):
        super().__init__(parent)
        
        self.app_controller = app_controller 
        self.employees_data = []
        
        self.current_config = initial_config
        
        self.ventas_file_path = os.path.join(BASE_DIR, "assets", "ventas_completadas.json")
        self.menu_file_path = os.path.join(BASE_DIR, "assets", "menu.json")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 25)
        main_layout.setSpacing(15)

        title = QLabel("Panel de Administración")
        title.setObjectName("section_title")

        main_layout.addWidget(title)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        employee_tab = QWidget()
        employee_layout = QVBoxLayout(employee_tab)
        employee_layout.setContentsMargins(15, 15, 15, 15)
        employee_layout.setSpacing(15)
        employee_controls_layout = QHBoxLayout()

        self.btn_add_employee = QPushButton("Añadir Empleado")
        self.btn_add_employee.setObjectName("orange_button")
        self.btn_edit_employee = QPushButton("Editar Empleado")
        self.btn_edit_employee.setObjectName("orange_button")
        self.btn_delete_employee = QPushButton("Eliminar Empleado")
        self.btn_delete_employee.setObjectName("orange_button")

        employee_controls_layout.addWidget(self.btn_add_employee)
        employee_controls_layout.addWidget(self.btn_edit_employee)
        employee_controls_layout.addWidget(self.btn_delete_employee)
        employee_controls_layout.addStretch()
        employee_layout.addLayout(employee_controls_layout)

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
        employee_layout.addWidget(self.employee_table)
        self.tab_widget.addTab(employee_tab, "Empleados")

        self.available_roles = []
        try:
            config_path = os.path.join(BASE_DIR, "assets", "config.json")
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                self.available_roles = list(config_data.get("roles_pago", {}).keys())
                if not self.available_roles:
                    print("No se encontraron roles en config.json. Usando lista por defecto.")
                    self.available_roles = ["Mesero", "Cajera", "Jefe de Cocina", "Michelero"]
        except (FileNotFoundError, json.JSONDecodeError):
            print("No se encontró config.json. Usando lista de roles por defecto.")
            self.available_roles = ["Mesero", "Cajera", "Jefe de Cocina", "Michelero"]

        tables_tab = QWidget()
        tables_layout = QVBoxLayout(tables_tab)
        tables_layout.setContentsMargins(15, 15, 15, 15)
        tables_layout.setSpacing(15)
        table_controls_layout = QHBoxLayout()
        table_controls_layout.addWidget(QLabel("Gestionar Mesas:"))

        self.btn_add_table = QPushButton("(+) Añadir Mesa")
        self.btn_add_table.setObjectName("orange_button")
        self.btn_remove_table = QPushButton("(-) Quitar Mesa")
        self.btn_remove_table.setObjectName("orange_button")

        table_controls_layout.addWidget(self.btn_add_table)
        table_controls_layout.addWidget(self.btn_remove_table)
        table_controls_layout.addStretch()
        tables_layout.addLayout(table_controls_layout)

        scroll_area_tables = QScrollArea()
        scroll_area_tables.setWidgetResizable(True)

        tables_layout.addWidget(scroll_area_tables)
        self.table_cards_container = QWidget()
        self.table_cards_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.table_grid_layout = QGridLayout(self.table_cards_container)
        self.table_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.table_grid_layout.setSpacing(20)
        cols = 5
        for col in range(cols):
            self.table_grid_layout.setColumnStretch(col, 1)
        scroll_area_tables.setWidget(self.table_cards_container)
        self.tab_widget.addTab(tables_tab, "Mesas")
        
        menu_tab = QWidget()
        menu_layout = QVBoxLayout(menu_tab)
        menu_layout.setContentsMargins(15, 15, 15, 15)
        menu_layout.setSpacing(15)
        
        self.btn_save_menu = QPushButton("Guardar Estado del Menú")
        self.btn_save_menu.setObjectName("orange_button")
        
        menu_layout.addWidget(self.btn_save_menu)
        
        self.menu_tree = QTreeWidget()
        self.menu_tree.setObjectName("menu_tree")
        self.menu_tree.setColumnCount(1) 
        self.menu_tree.setHeaderLabels(["Platillo / Categoría"])
        
        menu_header = self.menu_tree.header()
        menu_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.menu_tree.setStyleSheet("QTreeWidget::item { height: 60px; }") 
        
        menu_layout.addWidget(self.menu_tree)
        self.tab_widget.addTab(menu_tab, "Gestión de Menú")
        
        reportes_tab = QWidget()
        reportes_layout = QHBoxLayout(reportes_tab)
        reportes_tab.setLayout(reportes_layout)
        reportes_layout.setContentsMargins(15, 15, 15, 15)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(400) 
        
        left_layout.addWidget(QLabel("Seleccione un día:"))
        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("report_calendar")
        left_layout.addWidget(self.calendar)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.report_total_label = QLabel("Total de Ventas: C$ 0.00")
        self.report_total_label.setObjectName("section_title") 
        
        right_layout.addWidget(QLabel("Platillos más vendidos de ese día:"))
        self.report_table = QTableWidget()
        self.report_table.setObjectName("employee_table") 
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Platillo", "Cantidad Vendida"])
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.report_table.setColumnWidth(1, 150)
        
        right_layout.addWidget(self.report_total_label)
        right_layout.addWidget(self.report_table)
        reportes_layout.addWidget(left_panel)
        reportes_layout.addWidget(right_panel)
        self.tab_widget.addTab(reportes_tab, "Reportes")
        
        payroll_tab = QWidget()
        payroll_layout = QVBoxLayout(payroll_tab)
        payroll_tab.setLayout(payroll_layout)
        payroll_layout.setContentsMargins(15, 15, 15, 15)
        payroll_layout.setSpacing(15)

        controls_hbox = QHBoxLayout()
        payroll_layout.addLayout(controls_hbox)

        controls_hbox.addWidget(QLabel("Desde:"))
        self.payroll_start_date = QDateEdit()
        self.payroll_start_date.setCalendarPopup(True)
        self.payroll_start_date.setDate(QDate.currentDate().addMonths(-1))
        controls_hbox.addWidget(self.payroll_start_date)

        controls_hbox.addWidget(QLabel("Hasta:"))
        self.payroll_end_date = QDateEdit()
        self.payroll_end_date.setCalendarPopup(True)
        self.payroll_end_date.setDate(QDate.currentDate())
        controls_hbox.addWidget(self.payroll_end_date)

        self.btn_calculate_payroll = QPushButton("Calcular Nómina")
        self.btn_calculate_payroll.setObjectName("orange_button")
        controls_hbox.addWidget(self.btn_calculate_payroll)

        controls_hbox.addStretch() 

        self.btn_export_pdf = QPushButton("Exportar PDF Seleccionado")
        self.btn_export_pdf.setObjectName("orange_button")
        self.btn_export_pdf.setEnabled(False) 
        controls_hbox.addWidget(self.btn_export_pdf)
        
        self.btn_generate_random = QPushButton("Generar Datos Aleatorios (Test)")
        controls_hbox.addWidget(self.btn_generate_random)
        
        payroll_layout.addWidget(QLabel("Resultados de Nómina:"))
        self.payroll_table = QTableWidget()
        self.payroll_table.setObjectName("employee_table")
        self.payroll_table.setColumnCount(7) 
        self.payroll_table.setHorizontalHeaderLabels([
            "Empleado", "Rol", "Hrs Reg.", "Hrs Ext.",
            "Pago Reg. (C$)", "Pago Ext. (C$)", "Pago Total (C$)"
        ])
        payroll_header = self.payroll_table.horizontalHeader()
        payroll_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        payroll_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        payroll_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        payroll_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        payroll_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        payroll_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        payroll_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        
        self.payroll_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.payroll_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        payroll_layout.addWidget(self.payroll_table)
        self.tab_widget.addTab(payroll_tab, "Nómina")

        self.btn_add_employee.clicked.connect(self.add_employee)
        self.btn_edit_employee.clicked.connect(self.edit_employee)
        self.btn_delete_employee.clicked.connect(self.delete_employee)
        
        self.btn_add_table.clicked.connect(self.add_table)
        self.btn_remove_table.clicked.connect(self.remove_table)
        
        self.btn_save_menu.clicked.connect(self.save_menu_data)
        
        self.calendar.selectionChanged.connect(self.mostrar_reporte_del_dia)
        
        self.btn_calculate_payroll.clicked.connect(self.calculate_payroll)
        self.btn_export_pdf.clicked.connect(self.export_payroll_pdf)
        self.btn_generate_random.clicked.connect(self.generate_random_attendance)
        self.payroll_table.itemSelectionChanged.connect(self.update_export_button_state)

        self._load_initial_data()

    def _load_initial_data(self):
        print("Cargando datos iniciales de AdminPage desde la BD...")
        self.refresh_employee_table() 
        self.populate_table_cards()   
        self.load_menu_data()         
        self.mostrar_reporte_del_dia() 
        
    
    def populate_table_cards(self):
        while self.table_grid_layout.count():
            item = self.table_grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        total_mesas = self.current_config.get("total_mesas", 10)
        cols = 5
        for i in range(total_mesas):
            table_number = i + 1
            card = TableCardWidget(table_number)
            row = i // cols
            col = i % cols
            self.table_grid_layout.addWidget(card, row, col)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_grid_layout.addWidget(spacer, self.table_grid_layout.rowCount(), 0, 1, -1)
        self.btn_remove_table.setEnabled(total_mesas > 1)

    def add_table(self):
        current_total = self.current_config.get("total_mesas", 10)
        if current_total < 100:
            self.current_config["total_mesas"] = current_total + 1
            self.populate_table_cards()
            self._save_config_to_file()
            self._notify_server_config_change()
            self.config_updated.emit(self.current_config)
            
            print(f"Mesa añadida. Total: {self.current_config['total_mesas']}")
        else:
            QMessageBox.information(self, "Límite Alcanzado", "Se ha alcanzado el número máximo de mesas (100).")

    def remove_table(self):
        current_total = self.current_config.get("total_mesas", 10)
        if current_total > 1:
            self.current_config["total_mesas"] = current_total - 1
            self.populate_table_cards()
            self._save_config_to_file()
            self._notify_server_config_change()
            self.config_updated.emit(self.current_config)
            
            print(f"Mesa eliminada. Total: {self.current_config['total_mesas']}")
        else:
            QMessageBox.warning(self, "Acción no permitida", "Debe haber al menos una mesa.")

    def refresh_employee_table(self):
        print("Refrescando tabla de empleados desde la BD...")
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
        new_id, ok1 = QInputDialog.getText(self, 'Añadir Empleado', 'Ingrese el ID del nuevo empleado:')
        if not ok1 or not new_id.strip():
            print("Operación cancelada.")
            return

        new_id = new_id.strip()
        
        if self.app_controller.data_manager.get_employee_by_id(new_id):
            QMessageBox.warning(self, "Error", f"El ID '{new_id}' ya existe en la base de datos.")
            return

        new_name, ok2 = QInputDialog.getText(self, 'Añadir Empleado', 'Ingrese el nombre completo del nuevo empleado:')
        if not ok2 or not new_name.strip():
            print("Operación cancelada (Nombre).")
            return
        
        new_rol, ok3 = QInputDialog.getItem(self, "Añadir Empleado", "Seleccione el rol:", self.available_roles, 0, False)
        if not ok3 or not new_rol:
            print("Operación cancelada (Rol).")
            return
            
        new_name = new_name.strip()
        
        result = self.app_controller.agregar_empleado(new_id, new_name, new_rol)
        
        if result is None:
            QMessageBox.critical(self, "Error", f"No se pudo añadir el empleado {new_name} a la base de datos.")
            return
            
        print(f"✅ Empleado '{new_name}' (ID: {new_id}) añadido a la BD.")
        
        self.refresh_employee_table()
        

    def edit_employee(self):
        current_row = self.employee_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione un empleado para editar.")
            return
        
        original_id_item = self.employee_table.item(current_row, 0)
        original_id = original_id_item.text()
        
        original_employee = self.app_controller.data_manager.get_employee_by_id(original_id)
        if not original_employee:
            QMessageBox.critical(self, "Error", "No se pudo encontrar al empleado en la base de datos.")
            self.refresh_employee_table()
            return
            
        original_name = original_employee.get("nombre", "")
        original_rol = original_employee.get("rol", "")
        
        new_id, ok1 = QInputDialog.getText(self, 'Editar Empleado', 'ID:', QLineEdit.EchoMode.Normal, original_id)
        if not ok1 or not new_id.strip(): return
        new_id = new_id.strip()

        if new_id != original_id:
            if self.app_controller.data_manager.get_employee_by_id(new_id):
                QMessageBox.warning(self, "Error", f"El ID '{new_id}' ya está en uso.")
                return

        new_name, ok2 = QInputDialog.getText(self, 'Editar Empleado', 'Nombre Completo:', QLineEdit.EchoMode.Normal, original_name)
        if not ok2 or not new_name.strip(): return
        new_name = new_name.strip()

        try:
            current_role_index = self.available_roles.index(original_rol)
        except ValueError:
            current_role_index = 0 

        new_rol, ok3 = QInputDialog.getItem(self, "Editar Empleado", "Seleccione el rol:", self.available_roles, current_role_index, False)
        if not ok3 or not new_rol:
            print("Edición cancelada (Rol).")
            return
        
        self.app_controller.editar_empleado(original_id, new_id, new_name, new_rol)
        
        print(f"✅ Empleado (ID original: {original_id}) actualizado en la BD.")
        
        self.refresh_employee_table()
        

    def delete_employee(self):
        current_row = self.employee_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un empleado de la tabla para eliminar.")
            return

        id_item = self.employee_table.item(current_row, 0)
        name_item = self.employee_table.item(current_row, 1)
        employee_id = id_item.text()
        employee_name = name_item.text()
        
        confirm = QMessageBox.question(self, "Confirmar Eliminación", 
                                    f"¿Está seguro de que desea eliminar a '{employee_name}' (ID: {employee_id})?\n\n¡CUIDADO! Esto puede fallar si el empleado tiene un historial de asistencia.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            
            result = self.app_controller.eliminar_empleado(employee_id)
            
            if result is None:
                QMessageBox.critical(self, "Error de Borrado", f"No se pudo eliminar a '{employee_name}'.\nEs probable que tenga un historial de asistencia vinculado.")
                return
                
            print(f"✅ Empleado '{employee_name}' (ID: {employee_id}) eliminado de la BD.")
            
            self.refresh_employee_table()
            
        else:
            print("Operación cancelada.")
            
    
    def load_menu_data(self):
        self.menu_tree.clear() 
        
        try:
            menu_data = self.app_controller.data_manager.get_menu_with_categories()
            
            for categoria_data in menu_data.get("categorias", []):
                categoria_nombre = categoria_data.get("nombre", "Sin Categoría")
                parent_item = QTreeWidgetItem(self.menu_tree)
                parent_item.setText(0, categoria_nombre)
                parent_item.setData(0, Qt.ItemDataRole.UserRole, "categoria")
                parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                
                for item_data in categoria_data.get("items", []):
                    child_item = QTreeWidgetItem(parent_item)
                    
                    item_data_bool = item_data.copy()
                    item_data_bool['id'] = item_data_bool.get('id_item')
                    item_data_bool['disponible'] = bool(item_data.get('disponible', True))
                    
                    platillo_widget = PlatilloItemWidget(item_data_bool)
                    
                    self.menu_tree.setItemWidget(child_item, 0, platillo_widget)
                    
            self.menu_tree.expandAll()
            
        except Exception as e:
            print(f"Error inesperado al cargar menú desde BD: {e}")
            QMessageBox.critical(self, "Error de Menú", f"No se pudo cargar el menú desde la base de datos:\n{e}")

    def save_menu_data(self):
        print("Guardando estado del menú en la base de datos...")
        
        updates_to_make = []
        
        iterator = QTreeWidgetItemIterator(self.menu_tree)
        while iterator.value():
            item = iterator.value()
            widget = self.menu_tree.itemWidget(item, 0)
            if isinstance(widget, PlatilloItemWidget):
                updates_to_make.append((widget.item_id, widget.disponible))
            
            iterator += 1
            
        try:
            for item_id, disponible in updates_to_make:
                self.app_controller.data_manager.update_menu_item_availability(item_id, disponible)
            
            print(f"💾 Menú guardado exitosamente en la BD ({len(updates_to_make)} items actualizados)")
            QMessageBox.information(self, "Éxito", "El estado del menú se ha guardado correctamente.")

            try:
                    requests.post('http://127.0.0.1:5000/trigger_update', json={'event': 'menu_actualizado'})
            except requests.exceptions.RequestException as e:
                    print(f"⚠️ No se pudo notificar a los clientes (trigger_update): {e}")

        except Exception as e:
            print(f"Error: No se pudo escribir en la BD: {e}")
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo actualizar la base de datos:\n{e}")

    
    def mostrar_reporte_del_dia(self):
        selected_date = self.calendar.selectedDate().toPyDate()
        selected_date_str = selected_date.isoformat()
        
        print(f"📊 Generando reporte desde BD para {selected_date_str}...")

        total_ventas, items_vendidos = self.app_controller.data_manager.get_sales_report(selected_date_str)
        
        self.report_total_label.setText(f"Total de Ventas: C$ {total_ventas:.2f}")
        
        self.report_table.setRowCount(len(items_vendidos))
        for row, item in enumerate(items_vendidos):
            item_nombre = QTableWidgetItem(item["nombre"])
            item_cantidad = QTableWidgetItem(str(item["cantidad_total"]))
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.report_table.setItem(row, 0, item_nombre)
            self.report_table.setItem(row, 1, item_cantidad)
            
        print(f"📊 Reporte generado para {selected_date_str}. Total: C${total_ventas:.2f}")


    def calculate_payroll(self):
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()

        start_date = start_date_q.toPyDate()
        end_date_inclusive = end_date_q.toPyDate()
        end_date_exclusive = end_date_q.toPyDate() + datetime.timedelta(days=1)

        print(f"💰 Calculando nómina desde {start_date} hasta {end_date_inclusive}...")

        payroll_rates = self.current_config.get("roles_pago", {})
        if not payroll_rates:
            QMessageBox.critical(self, "Error de Configuración", "No se encontraron tarifas de pago.")
            return

        self.employees_data = self.app_controller.get_todos_los_empleados()
        employees_dict = {emp['id_empleado']: emp for emp in self.employees_data}

        attendance_history_rows = self.app_controller.data_manager.get_attendance_history_range(
            start_date.isoformat(), 
            end_date_exclusive.isoformat()
        )
        
        if not attendance_history_rows:
            print("No se encontró historial de asistencia en ese rango.")
            self.payroll_table.setRowCount(0)
            return

        payroll_results = {}
        self.payroll_daily_details = {}

        valid_entries = []
        for entry in attendance_history_rows:
            try:
                ts = datetime.datetime.fromisoformat(entry['timestamp'])
                valid_entries.append({
                    "employee_id": entry['id_empleado'],
                    "timestamp": ts, 
                    "type": entry['tipo']
                })
            except (ValueError, KeyError): 
                continue
            
        valid_entries.sort(key=lambda x: (x['employee_id'], x['timestamp']))

        last_entry_time = None

        for entry in valid_entries:
            emp_id = entry['employee_id']
            ts = entry['timestamp']
            entry_type = entry['type']
            day_str = ts.date().isoformat()

            if emp_id not in payroll_results:
                payroll_results[emp_id] = {"total_reg_mins": 0, "total_ot_mins": 0, "total_pay": 0.0, "total_reg_pay": 0.0, "total_ot_pay": 0.0}
            if emp_id not in self.payroll_daily_details:
                self.payroll_daily_details[emp_id] = {}
            if day_str not in self.payroll_daily_details[emp_id]:
                self.payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0}


            if entry_type == "entrada":
                if self.payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                    self.payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                last_entry_time = ts 

            elif entry_type == "salida" and last_entry_time is not None and last_entry_time.date() == ts.date():

                jornada_start_time = last_entry_time.replace(hour=12, minute=0, second=0, microsecond=0)

                start_time_for_calc = max(last_entry_time, jornada_start_time)
                if ts > start_time_for_calc: 
                    duration = ts - start_time_for_calc
                    total_minutes_shift = duration.total_seconds() / 60
                else:
                    total_minutes_shift = 0 

                employee_info = employees_dict.get(emp_id)
                rol = employee_info.get("rol") if employee_info else None
                rate_info = payroll_rates.get(rol) if rol else None

                if rate_info and "minuto" in rate_info and total_minutes_shift > 0:
                    rate_per_minute = rate_info["minuto"]

                    overtime_start_time = start_time_for_calc.replace(hour=22, minute=0, second=0, microsecond=0)
                    regular_minutes_shift = 0
                    overtime_minutes_shift = 0

                    if ts <= overtime_start_time:
                        regular_minutes_shift = total_minutes_shift
                    elif start_time_for_calc < overtime_start_time < ts:
                        regular_duration = overtime_start_time - start_time_for_calc
                        regular_minutes_shift = regular_duration.total_seconds() / 60
                        overtime_duration = ts - overtime_start_time
                        overtime_minutes_shift = overtime_duration.total_seconds() / 60
                    else: 
                        overtime_minutes_shift = total_minutes_shift

                    reg_pay_shift = regular_minutes_shift * rate_per_minute
                    ot_pay_shift = overtime_minutes_shift * rate_per_minute * 2
                    shift_pay = reg_pay_shift + ot_pay_shift

                    payroll_results[emp_id]["total_reg_mins"] += regular_minutes_shift
                    payroll_results[emp_id]["total_ot_mins"] += overtime_minutes_shift
                    payroll_results[emp_id]["total_reg_pay"] += reg_pay_shift 
                    payroll_results[emp_id]["total_ot_pay"] += ot_pay_shift   
                    payroll_results[emp_id]["total_pay"] += shift_pay       

                    self.payroll_daily_details[emp_id][day_str]["reg_mins"] += regular_minutes_shift
                    self.payroll_daily_details[emp_id][day_str]["ot_mins"] += overtime_minutes_shift
                    self.payroll_daily_details[emp_id][day_str]["pay"] += shift_pay
                    self.payroll_daily_details[emp_id][day_str]["last_exit"] = ts 

                    last_entry_time = None 
                else: 
                    if total_minutes_shift <= 0:
                        print(f"Info: No se calculó tiempo pagable para {emp_id} el {day_str} (salida antes/igual a 12PM).")
                    else:
                        print(f"Advertencia: No se pudo calcular pago para {emp_id} el {day_str} (rol '{rol}' o tarifa inválida).")
                    self.payroll_daily_details[emp_id][day_str]["last_exit"] = ts 
                    last_entry_time = None

            elif last_entry_time is not None and last_entry_time.date() != ts.date():
                last_entry_time = None
                if entry_type == "entrada": 
                    if day_str not in self.payroll_daily_details[emp_id]: 
                        self.payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0}
                    if self.payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                        self.payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                    last_entry_time = ts


        self.payroll_table.setRowCount(0)
        self.payroll_table.setRowCount(len(payroll_results))

        row = 0
        for emp_id, results in payroll_results.items():
            employee_info = employees_dict.get(emp_id)
            if not employee_info: continue

            reg_hours = int(results["total_reg_mins"] // 60)
            reg_mins = int(results["total_reg_mins"] % 60)
            ot_hours = int(results["total_ot_mins"] // 60)
            ot_mins = int(results["total_ot_mins"] % 60)

            item_name = QTableWidgetItem(employee_info.get("nombre", "Desconocido"))
            item_rol = QTableWidgetItem(employee_info.get("rol", "N/A"))
            item_hrs_reg = QTableWidgetItem(f"{reg_hours:02d}:{reg_mins:02d}")
            item_hrs_ot = QTableWidgetItem(f"{ot_hours:02d}:{ot_mins:02d}")
            item_pay_reg = QTableWidgetItem(f"C$ {results['total_reg_pay']:.2f}") 
            item_pay_ot = QTableWidgetItem(f"C$ {results['total_ot_pay']:.2f}")   
            item_pay_total = QTableWidgetItem(f"C$ {results['total_pay']:.2f}")

            item_name.setData(Qt.ItemDataRole.UserRole, emp_id)
            item_hrs_reg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_hrs_ot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pay_reg.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pay_ot.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pay_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.payroll_table.setItem(row, 0, item_name)
            self.payroll_table.setItem(row, 1, item_rol)
            self.payroll_table.setItem(row, 2, item_hrs_reg)
            self.payroll_table.setItem(row, 3, item_hrs_ot)
            self.payroll_table.setItem(row, 4, item_pay_reg)
            self.payroll_table.setItem(row, 5, item_pay_ot)
            self.payroll_table.setItem(row, 6, item_pay_total)
            row += 1
            
        self.update_export_button_state()
        print(f"✅ Nómina calculada y mostrada para {len(payroll_results)} empleados. Detalles diarios guardados para PDF.")


    def export_payroll_pdf(self):
        selected_rows = self.payroll_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione un empleado de la tabla para exportar.")
            return
            
        selected_row_index = selected_rows[0].row()
        
        employee_name_item = self.payroll_table.item(selected_row_index, 0)
        employee_rol_item = self.payroll_table.item(selected_row_index, 1)
        
        if not employee_name_item or not employee_rol_item:
            QMessageBox.warning(self, "Error", "No se pudo obtener la información del empleado seleccionado.")
            return

        employee_name = employee_name_item.text()
        employee_rol = employee_rol_item.text()
        employee_id = employee_name_item.data(Qt.ItemDataRole.UserRole) 

        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        start_date = start_date_q.toPyDate()
        end_date = end_date_q.toPyDate() 

        print(f"📄 Preparando PDF para {employee_name} (ID: {employee_id}) del {start_date} al {end_date}...")

        employee_daily_details = self.payroll_daily_details.get(employee_id, {})

        if not employee_daily_details:
            QMessageBox.information(self, "Sin Datos", f"No se encontraron registros de asistencia calculados para {employee_name} en el período seleccionado.")
            return

        default_filename = f"Nomina_{employee_name.replace(' ', '_')}_{start_date}_a_{end_date}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", default_filename, "PDF Files (*.pdf)")

        if not save_path:
            print("Exportación cancelada por el usuario.")
            return

        try:
            pdf = FPDF()
            pdf.add_page()
            
            logo_path = os.path.join(BASE_DIR,"Assets","logopdf.png") 
            if os.path.exists(logo_path):
                pdf.image(logo_path, x=5, y=5, w=50) 
                pdf.ln(20) 
            else:
                print(f"⚠️ Advertencia: No se encontró el logo en {logo_path}")
                pdf.ln(20) 

            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Reporte de Nómina", 0, 1, 'C')
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 7, f"Empleado: {employee_name}", 0, 1)
            pdf.cell(0, 7, f"Rol: {employee_rol}", 0, 1)
            pdf.cell(0, 7, f"Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}", 0, 1)
            pdf.ln(10)

            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(230, 230, 230) 
            col_widths = [25, 30, 30, 30, 30, 45] 
            headers = ["Fecha", "Entrada", "Salida", "Hrs Reg.", "Hrs Ext.", "Pago Diario (C$)"] 
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, 1, 0, 'C', fill=True)
            pdf.ln()

            pdf.set_font("Arial", size=10)
            total_period_reg_mins = 0
            total_period_ot_mins = 0
            total_period_pay = 0.0
            
            sorted_days = sorted(employee_daily_details.keys()) 

            for day_str in sorted_days:
                details = employee_daily_details[day_str] 
                
                fecha = datetime.date.fromisoformat(day_str).strftime('%d/%m/%y')
                entrada = details['first_entry'].strftime('%I:%M %p') if details['first_entry'] else "-"
                salida = details['last_exit'].strftime('%I:%M %p') if details['last_exit'] else "-"

                reg_h = int(details["reg_mins"] // 60)
                reg_m = int(details["reg_mins"] % 60)
                hrs_reg = f"{reg_h:02d}:{reg_m:02d}" if details['reg_mins'] > 0 or details['ot_mins'] > 0 else "-"

                ot_h = int(details["ot_mins"] // 60)
                ot_m = int(details["ot_mins"] % 60)
                hrs_ot = f"{ot_h:02d}:{ot_m:02d}" if details['ot_mins'] > 0 else "00:00"

                pago_diario = f"{details['pay']:.2f}" if details['reg_mins'] > 0 or details['ot_mins'] > 0 else "-"

                pdf.cell(col_widths[0], 7, fecha, 1, 0, 'C')
                pdf.cell(col_widths[1], 7, entrada, 1, 0, 'C')
                pdf.cell(col_widths[2], 7, salida, 1, 0, 'C')
                pdf.cell(col_widths[3], 7, hrs_reg, 1, 0, 'C')
                pdf.cell(col_widths[4], 7, hrs_ot, 1, 0, 'C')
                pdf.cell(col_widths[5], 7, pago_diario, 1, 0, 'R') 
                pdf.ln()

                if details['reg_mins'] > 0 or details['ot_mins'] > 0: 
                    total_period_reg_mins += details["reg_mins"]
                    total_period_ot_mins += details["ot_mins"]
                    total_period_pay += details["pay"]

            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_widths[0] + col_widths[1] + col_widths[2], 8, "TOTALES:", 1, 0, 'R', fill=True)
            
            total_reg_h = int(total_period_reg_mins // 60)
            total_reg_m = int(total_period_reg_mins % 60)
            total_ot_h = int(total_period_ot_mins // 60)
            total_ot_m = int(total_period_ot_mins % 60)
            
            pdf.cell(col_widths[3], 8, f"{total_reg_h:02d}:{total_reg_m:02d}", 1, 0, 'C', fill=True) 
            pdf.cell(col_widths[4], 8, f"{total_ot_h:02d}:{total_ot_m:02d}", 1, 0, 'C', fill=True) 
            pdf.cell(col_widths[5], 8, f"C$ {total_period_pay:.2f}", 1, 0, 'R', fill=True) 
            pdf.ln(15)

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Pago Total del Período: C$ {total_period_pay:.2f}", 0, 1)

            pdf.output(save_path, "F")
            print(f"✅ PDF guardado exitosamente en: {save_path}")
            QMessageBox.information(self, "Éxito", f"El reporte PDF para {employee_name} se ha guardado correctamente.")

        except Exception as e:
            print(f"Error al generar el PDF: {e}")
            QMessageBox.critical(self, "Error de PDF", f"Ocurrió un error al generar el archivo PDF:\n{e}")

    def generate_random_attendance(self):
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        
        start_date = start_date_q.toPyDate()
        end_date = end_date_q.toPyDate()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Fechas Inválidas", "La fecha de inicio no puede ser posterior a la fecha de fin.")
            return
            
        print(f"Preparando para generar datos aleatorios desde {start_date} hasta {end_date}...")
        
        confirm = QMessageBox.warning(self, "Confirmar Generación de Datos", 
                                    "Esto añadirá registros de entrada/salida aleatorios a la base de datos "
                                    "para el período seleccionado. Esto es útil para probar la nómina.\n\n"
                                    "NO afectará el estado actual mostrado en la pestaña 'Control de Asistencia'.\n\n"
                                    "¿Está seguro de que desea continuar?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.No:
            print("Operación cancelada.")
            return

        current_employees = self.app_controller.data_manager.get_employees()
        if not current_employees:
            QMessageBox.critical(self, "Error", "No se pudieron cargar los datos de empleados desde la BD.")
            return
            
        new_entries_batch = []
        
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                for employee in current_employees:
                    emp_id = employee.get("id_empleado")
                    if not emp_id: continue
                    
                    if random.random() < 0.9: 
                        try:
                            entry_hour = 12
                            entry_minute = random.randint(-15, 15)
                            entry_time = datetime.datetime(current_date.year, current_date.month, current_date.day, 
                                                        entry_hour, 0, 0) + datetime.timedelta(minutes=entry_minute)
                            
                            exit_hour = 22
                            exit_minute = random.randint(-15, 60)
                            exit_time = datetime.datetime(current_date.year, current_date.month, current_date.day,
                                                        exit_hour, 0, 0) + datetime.timedelta(minutes=exit_minute)

                            if exit_time > entry_time:
                                new_entries_batch.append((
                                    emp_id,
                                    entry_time.isoformat(timespec='seconds'),
                                    "entrada"
                                ))
                                new_entries_batch.append((
                                    emp_id,
                                    exit_time.isoformat(timespec='seconds'),
                                    "salida"
                                ))
                        except ValueError: 
                            print(f"Error generando fecha para {emp_id} en {current_date}")

            current_date += datetime.timedelta(days=1)

        if not new_entries_batch:
            print("No se generaron nuevos eventos.")
            QMessageBox.information(self, "Éxito", "No se generaron nuevos datos (posiblemente solo eran fines de semana).")
            return

        success = self.app_controller.data_manager.add_attendance_events_batch(new_entries_batch)
        
        if success:
            print(f"{len(new_entries_batch)} registros aleatorios añadidos a la BD")
            QMessageBox.information(self, "Éxito", f"Se generaron y añadieron {len(new_entries_batch)//2} días de trabajo aleatorios al historial.")
            self.calculate_payroll()
        else:
            print(f"Error al guardar el historial de asistencia en la BD.")
            QMessageBox.critical(self, "Error", "No se pudo guardar el archivo de historial de asistencia.")

    def update_export_button_state(self):
        has_selection = bool(self.payroll_table.selectionModel().selectedRows())
        self.btn_export_pdf.setEnabled(has_selection)

    def _save_config_to_file(self):
        """Guarda la configuración actual en el archivo JSON."""
        config_path = os.path.join(BASE_DIR, "assets", "config.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(self.current_config, f, indent=4)
            print("Configuración guardada en config.json")
        except Exception as e:
            print(f"Error guardando config.json: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración:\n{e}")
    
    def _notify_server_config_change(self):
        """Avisa al servidor que la configuración ha cambiado, INCLUYENDO LA API KEY."""
        try:
            url = 'http://127.0.0.1:5000/trigger_update'
            
            api_key = self.app_controller.API_KEY 
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }

            payload = {'event': 'configuracion_actualizada'}
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                print("📡 Notificación enviada correctamente al servidor.")
            else:
                print(f"Servidor rechazó la notificación. Código: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"No se pudo conectar con el servidor: {e}")
    
