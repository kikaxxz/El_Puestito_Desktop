import os
import json
import datetime
import random
import requests
import shutil 
from fpdf import FPDF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QLineEdit, QFrame, QHeaderView, QTableWidgetItem, QDialog,
    QScrollArea, QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QTabWidget, QGridLayout, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QGraphicsOpacityEffect, QTreeWidgetItemIterator,
    QCalendarWidget, QDateEdit, QFileDialog, QLayout, QFormLayout, 
    QComboBox, QDoubleSpinBox, QTextEdit, QAbstractItemView, QSpinBox
)

from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl, QTimer, Qt, pyqtSignal, QDate
from PyQt6.QtGui import QPixmap
from widgets.table_card_widget import TableCardWidget
from widgets.platillo_item import PlatilloItemWidget
from logger_setup import setup_logger

logger = setup_logger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EmployeeFormDialog(QDialog):
    def __init__(self, parent=None, employee_data=None, available_roles=[], api_key=""):
        super().__init__(parent)
        self.setWindowTitle("Datos del Empleado")
        self.setFixedSize(400, 350)
        self.api_key = api_key
        self.fingerprint_id = employee_data.get('fingerprint_id') if employee_data else None
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.inp_id = QLineEdit(employee_data.get('id_empleado', '') if employee_data else '')
        self.inp_name = QLineEdit(employee_data.get('nombre', '') if employee_data else '')
        
        self.combo_rol = QComboBox()
        self.combo_roles = available_roles
        self.combo_rol.addItems(self.combo_roles)
        if employee_data and employee_data.get('rol') in self.combo_roles:
            self.combo_rol.setCurrentText(employee_data.get('rol'))
            
        form_layout.addRow("ID Empleado:", self.inp_id)
        form_layout.addRow("Nombre Completo:", self.inp_name)
        form_layout.addRow("Rol:", self.combo_rol)
        layout.addLayout(form_layout)
        
        layout.addWidget(QLabel("--- Registro Biométrico ---"))
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 3) 
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False) 
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f76606; }")
        
        layout.addWidget(self.progress_bar) 

        bio_layout = QHBoxLayout()
        self.lbl_finger_status = QLabel()
        self.lbl_finger_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_finger_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #888;")
        self.update_finger_label()
        
        
        self.btn_scan = QPushButton("Escanear Huella")
        self.btn_scan.setObjectName("blue_button")
        self.btn_scan.clicked.connect(self.start_scan_process)
        
        bio_layout.addWidget(self.lbl_finger_status)
        bio_layout.addWidget(self.btn_scan)
        layout.addLayout(bio_layout)
        
        layout.addStretch()
        
        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self.accept) 
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject) 
        
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)
        
        self.poll_timer = QTimer(self)
        self.poll_timer.interval = 1000
        self.poll_timer.timeout.connect(self.check_enroll_status)

    def closeEvent(self, event):
        self.poll_timer.stop()
        super().closeEvent(event)

    def reject(self):
        self.poll_timer.stop()
        super().reject()

    def accept(self):
        self.poll_timer.stop()
        super().accept()

    def update_finger_label(self):
        if self.fingerprint_id:
            self.lbl_finger_status.setText(f"Huella ID: {self.fingerprint_id}")
            self.lbl_finger_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.lbl_finger_status.setText("Sin Huella")
            self.lbl_finger_status.setStyleSheet("color: red;")

    def start_scan_process(self):
        try:
            url = 'http://127.0.0.1:5000/api/biometric/start-enroll'
            headers = {'X-API-KEY': self.api_key}
            requests.post(url, headers=headers)
            
            self.btn_scan.setEnabled(False)
            self.btn_scan.setText("Esperando sensor...")
            
            self.poll_timer.stop()
            self.poll_timer.start() 
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo conectar al servidor: {e}")
            self.btn_scan.setEnabled(True)
            self.btn_scan.setText("Reintentar")

    def check_enroll_status(self):
        try:
            url = 'http://127.0.0.1:5000/api/biometric/check-enroll-status'
            resp = requests.get(url, timeout=1)
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data.get('status') == 'done':
                    self.fingerprint_id = data.get('finger_id')
                    self.poll_timer.stop()
                    
                    self.progress_bar.setValue(3) 
                    self.lbl_finger_status.setText(f"¡ÉXITO! ID Asignado: {self.fingerprint_id}")
                    self.lbl_finger_status.setStyleSheet("color: #00d26a; font-weight: bold;")
                    
                    self.btn_scan.setText("Escanear Nueva")
                    self.btn_scan.setEnabled(True)
                elif data.get('status') == 'in_progress':
                    step = data.get('step', 0)
                    msg = data.get('message', '...')
                    
                    self.progress_bar.setValue(step)
                    self.lbl_finger_status.setText(msg)
                    
                    if step == 1: 
                        self.lbl_finger_status.setStyleSheet("color: #ff9800; font-weight: bold;")
                    elif step == 2:
                        self.lbl_finger_status.setStyleSheet("color: #2196f3; font-weight: bold;")
                    else:
                        self.lbl_finger_status.setStyleSheet("color: #ccc;")

        except Exception as e:
            print(f"Error polling: {e}")

    def get_data(self):
        return {
            'id': self.inp_id.text().strip(),
            'nombre': self.inp_name.text().strip(),
            'rol': self.combo_rol.currentText(),
            'fingerprint_id': self.fingerprint_id
        }

class CategoryFormDialog(QDialog):
    """Diálogo simple para crear nuevas categorías."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Categoría")
        self.setFixedSize(300, 150)
        layout = QFormLayout(self)
        
        self.inp_nombre = QLineEdit()
        self.combo_destino = QComboBox()
        self.combo_destino.addItems(["cocina", "barra"])
        
        layout.addRow("Nombre Categoría:", self.inp_nombre)
        layout.addRow("Destino Impresión:", self.combo_destino)
        
        self.btn_save = QPushButton("Guardar")
        self.btn_save.setObjectName("orange_button")
        self.btn_save.clicked.connect(self.accept)
        layout.addRow(self.btn_save)

    def get_data(self):
        return {
            "nombre": self.inp_nombre.text().strip(),
            "destino": self.combo_destino.currentText()
        }

class MenuItemFormDialog(QDialog):
    """Diálogo estructurado para usar con style.qss externo."""
    def __init__(self, parent=None, item_data=None, categories=[]):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Platillo")
        self.setFixedSize(700, 450)
        
        self.image_path = item_data.get('imagen') if item_data else None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)
        
        title_lbl = QLabel("Detalles del Producto")
        title_lbl.setObjectName("section_title") 
        main_layout.addWidget(title_lbl)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.inp_nombre = QLineEdit(item_data.get('nombre', '') if item_data else '')
        self.inp_nombre.setPlaceholderText("Ej. Alitas BBQ")
        self.inp_nombre.setObjectName("dialog_input")
        
        self.inp_precio = QDoubleSpinBox()
        self.inp_precio.setRange(0, 99999)
        self.inp_precio.setPrefix("C$ ")
        self.inp_precio.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.inp_precio.setValue(float(item_data.get('precio', 0.0)) if item_data else 0.0)
        self.inp_precio.setObjectName("dialog_input")
        
        self.combo_cat = QComboBox()
        self.combo_cat.addItems([c['nombre'] for c in categories])
        if item_data and 'categoria_nombre' in item_data:
            self.combo_cat.setCurrentText(item_data['categoria_nombre'])
        self.combo_cat.setObjectName("dialog_input")

        self.inp_desc = QTextEdit()
        self.inp_desc.setPlaceholderText("Ingredientes, alérgenos, detalles...")
        self.inp_desc.setMaximumHeight(80)
        if item_data: self.inp_desc.setText(item_data.get('descripcion', ''))
        self.inp_desc.setObjectName("dialog_input")

        lbl_nombre = QLabel("Nombre:")
        lbl_nombre.setStyleSheet("font-weight: bold; color: #ccc;") 
        lbl_precio = QLabel("Precio:")
        lbl_precio.setStyleSheet("font-weight: bold; color: #ccc;")
        lbl_cat = QLabel("Categoría:")
        lbl_cat.setStyleSheet("font-weight: bold; color: #ccc;")
        lbl_desc = QLabel("Descripción:")
        lbl_desc.setStyleSheet("font-weight: bold; color: #ccc;")

        form_layout.addRow(lbl_nombre, self.inp_nombre)
        form_layout.addRow(lbl_precio, self.inp_precio)
        form_layout.addRow(lbl_cat, self.combo_cat)
        form_layout.addRow(lbl_desc, self.inp_desc)
        
        content_layout.addLayout(form_layout, stretch=3) 

        img_layout = QVBoxLayout()
        img_layout.setSpacing(10)
        img_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.lbl_image_preview = QLabel("Sin Imagen")
        self.lbl_image_preview.setObjectName("img_preview") 
        self.lbl_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image_preview.setFixedSize(200, 200) 
        self.lbl_image_preview.setScaledContents(True) 
        
        if self.image_path:
            self._load_preview(self.image_path)
            
        btn_img = QPushButton("Seleccionar Foto")
        btn_img.setObjectName("secondary_button") 
        btn_img.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_img.clicked.connect(self.select_image)
        
        img_layout.addWidget(QLabel("Fotografía:"))
        img_layout.addWidget(self.lbl_image_preview)
        img_layout.addWidget(btn_img)
        
        content_layout.addLayout(img_layout, stretch=2) 
        
        main_layout.addLayout(content_layout)
        
        btn_box = QHBoxLayout()
        btn_box.addStretch() 
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondary_button") 
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Guardar Cambios")
        save_btn.setObjectName("orange_button") 
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        
        main_layout.addLayout(btn_box)

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Imágenes (*.png *.jpg *.jpeg)")
        if file_name:
            self.image_path = file_name
            self._load_preview(file_name)

    def _load_preview(self, path):
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, "assets", path)
            
        if os.path.exists(path):
            pix = QPixmap(path)
            pix = pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.lbl_image_preview.setPixmap(pix)
        else:
            self.lbl_image_preview.setText("Imagen no encontrada")

    def get_data(self):
        return {
            'nombre': self.inp_nombre.text().strip(),
            'precio': self.inp_precio.value(),
            'descripcion': self.inp_desc.toPlainText(),
            'categoria_nombre': self.combo_cat.currentText(),
            'imagen_path': self.image_path
        }
    
class ComboBuilderTab(QWidget):
    combo_creado = pyqtSignal()
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.selected_items = {} 
        self.image_path = None
        
        main_layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("1. Selecciona Productos:"))
        
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.source_list.setStyleSheet("background: #2b2b2b; color: white; border-radius: 5px;")
        left_layout.addWidget(self.source_list)
        
        btn_add = QPushButton("Añadir al Combo >>")
        btn_add.setObjectName("blue_button") 
        btn_add.clicked.connect(self.add_item_to_combo)
        left_layout.addWidget(btn_add)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("2. Contenido del Combo:"))
        
        self.target_list = QTableWidget()
        self.target_list.setColumnCount(3)
        self.target_list.setHorizontalHeaderLabels(["Cant.", "Producto", "Quitar"])
        self.target_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.target_list.setStyleSheet("background: #1e1e24; color: white;")
        right_layout.addWidget(self.target_list)
        
        form_layout = QFormLayout()
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Ej: Combo Alitas + Cerveza")
        
        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 99999)
        self.inp_price.setPrefix("C$ ")
        self.inp_price.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        
        self.lbl_img_status = QLabel("Sin Imagen")
        self.lbl_img_status.setStyleSheet("color: #777; font-style: italic;")
        
        btn_img = QPushButton("Cargar Foto...")
        btn_img.setStyleSheet("background-color: #444; color: white; padding: 5px;")
        btn_img.clicked.connect(self.select_image)
        
        form_layout.addRow("Nombre Combo:", self.inp_name)
        form_layout.addRow("Precio Final:", self.inp_price)
        form_layout.addRow(self.lbl_img_status, btn_img)
        
        right_layout.addLayout(form_layout)
        
        btn_create = QPushButton("CREAR PROMOCIÓN")
        btn_create.setObjectName("orange_button")
        btn_create.setFixedHeight(50)
        btn_create.clicked.connect(self.save_combo)
        right_layout.addWidget(btn_create)
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)
        
        self.refresh_source_list()

    def refresh_source_list(self):
        self.source_list.clear()
        items = self.app_controller.data_manager.fetchall("SELECT id_item, nombre FROM menu_items WHERE disponible=1")
        for item in items:
            if "COMBO" not in item['id_item']: 
                list_item = QListWidgetItem(item['nombre'])
                list_item.setData(Qt.ItemDataRole.UserRole, item['id_item'])
                self.source_list.addItem(list_item)

    def add_item_to_combo(self):
        current_item = self.source_list.currentItem()
        if not current_item: return
        
        item_id = current_item.data(Qt.ItemDataRole.UserRole)
        item_name = current_item.text()
        
        if item_id in self.selected_items:
            self.selected_items[item_id]['qty'] += 1
        else:
            self.selected_items[item_id] = {'nombre': item_name, 'qty': 1}
            
        self.render_target_list()

    def remove_item(self, item_id):
        if item_id in self.selected_items:
            del self.selected_items[item_id]
            self.render_target_list()

    def render_target_list(self):
        self.target_list.setRowCount(0)
        self.target_list.setRowCount(len(self.selected_items))
        
        for row, (uid, data) in enumerate(self.selected_items.items()):
            qty_item = QTableWidgetItem(str(data['qty']))
            name_item = QTableWidgetItem(data['nombre'])
            
            btn_del = QPushButton("X")
            btn_del.setStyleSheet("color: red; font-weight: bold; border: none;")
            btn_del.clicked.connect(lambda _, x=uid: self.remove_item(x))
            
            self.target_list.setItem(row, 0, qty_item)
            self.target_list.setItem(row, 1, name_item)
            self.target_list.setCellWidget(row, 2, btn_del)

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Foto", "", "Imágenes (*.png *.jpg *.jpeg)")
        if file_name:
            self.image_path = file_name
            self.lbl_img_status.setText(os.path.basename(file_name))
            self.lbl_img_status.setStyleSheet("color: #4caf50;")

    def save_combo(self):
        name = self.inp_name.text().strip()
        price = self.inp_price.value()
        
        if not name or not self.selected_items:
            QMessageBox.warning(self, "Faltan datos", "Debes poner un nombre y agregar productos.")
            return
            
        desc_parts = []
        for uid, data in self.selected_items.items():
            desc_parts.append(f"{data['qty']}x {data['nombre']}")
        
        full_desc = "Incluye: " + ", ".join(desc_parts)
        final_img = ""
        if self.image_path:
            try:
                import shutil
                ext = os.path.splitext(self.image_path)[1]
                final_img = f"combo_{random.randint(1000,9999)}{ext}"
                dest = os.path.join(BASE_DIR, "assets", final_img)
                shutil.copy(self.image_path, dest)
            except: pass

        self.app_controller.data_manager.create_combo_item(name, price, full_desc, final_img)
        self.combo_creado.emit()

        QMessageBox.information(self, "¡Listo!", f"El '{name}' ha sido creado en la categoría Promociones.")
        self.selected_items = {}
        self.inp_name.clear()
        self.inp_price.setValue(0)
        self.image_path = None
        self.lbl_img_status.setText("Sin Imagen")
        self.render_target_list()

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
        self.btn_format_sensor = QPushButton("Formatear Sensor")
        self.btn_format_sensor.setStyleSheet("""
            background-color: #D32F2F; 
            color: white; 
            font-weight: bold; 
            padding: 5px; 
            border-radius: 5px;
        """)
        self.btn_format_sensor.setFixedWidth(150)

        employee_controls_layout.addWidget(self.btn_add_employee)
        employee_controls_layout.addWidget(self.btn_edit_employee)
        employee_controls_layout.addWidget(self.btn_delete_employee)
        employee_controls_layout.addStretch()
        employee_controls_layout.addWidget(self.btn_format_sensor)
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
                    self.available_roles = ["Mesero", "Cajera", "Jefe de Cocina", "Michelero"]
        except (FileNotFoundError, json.JSONDecodeError):
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
        menu_layout.setSpacing(10)
        
        menu_controls = QHBoxLayout()
        
        self.btn_add_cat = QPushButton("Nueva Categoría")
        self.btn_add_cat.setObjectName("orange_button")

        self.btn_add_item = QPushButton("Nuevo Platillo")
        self.btn_add_item.setObjectName("orange_button")
        
        self.btn_edit_item = QPushButton("Editar Seleccionado")
        self.btn_delete_item = QPushButton("Eliminar (Permanente)")
        self.btn_delete_item.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        
        menu_controls.addWidget(self.btn_add_cat)
        menu_controls.addWidget(self.btn_add_item)
        menu_controls.addStretch()
        menu_controls.addWidget(self.btn_edit_item)
        menu_controls.addWidget(self.btn_delete_item)
        
        menu_layout.addLayout(menu_controls)
        
        # Árbol del menú
        self.menu_tree = QTreeWidget()
        self.menu_tree.setObjectName("menu_tree")
        self.menu_tree.setColumnCount(1) 
        self.menu_tree.setHeaderLabels(["Platillo / Categoría"])
        menu_header = self.menu_tree.header()
        menu_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.menu_tree.setStyleSheet("QTreeWidget::item { height: 60px; }")
        
        self.menu_tree.itemDoubleClicked.connect(self.editar_platillo) 
        
        menu_layout.addWidget(self.menu_tree)
        self.btn_save_menu = QPushButton("Guardar Disponibilidad (ON/OFF)")
        menu_layout.addWidget(self.btn_save_menu)
        self.tab_widget.addTab(menu_tab, "Gestión de Menú")
        self.promo_builder = ComboBuilderTab(self.app_controller)
        self.promo_builder.combo_creado.connect(self.load_menu_data) 
        self.promo_builder.combo_creado.connect(self._notify_server_config_change)
        self.tab_widget.addTab(self.promo_builder, "Crear Promociones")

        reportes_tab = QWidget()
        reportes_layout = QVBoxLayout(reportes_tab)
        reportes_layout.setContentsMargins(20, 20, 20, 20)
        reportes_layout.setSpacing(20)
        
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)
        
        cal_wrapper = QWidget()
        cal_layout = QVBoxLayout(cal_wrapper)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.setSpacing(5)
        
        lbl_fecha = QLabel("Seleccione fecha:")
        lbl_fecha.setStyleSheet("font-size: 16px; font-weight: bold; color: #dddddd;")
        cal_layout.addWidget(lbl_fecha)
        
        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("report_calendar")
        self.calendar.setGridVisible(True)
        self.calendar.setFixedSize(400, 280)
        cal_layout.addWidget(self.calendar)
        
        self.stats_card = QFrame()
        self.stats_card.setObjectName("stats_card")
        self.stats_card.setStyleSheet("""
            QFrame#stats_card {
                background-color: #2b2b2b; 
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
            QLabel { color: white; }
        """)
        
        stats_layout = QVBoxLayout(self.stats_card)
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.setSpacing(5)
        
        lbl_titulo_ventas = QLabel("VENTAS TOTALES DEL DÍA")
        lbl_titulo_ventas.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        lbl_titulo_ventas.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaaaaa; letter-spacing: 1px;") 
        stats_layout.addWidget(lbl_titulo_ventas)

        self.report_total_label = QLabel("C$ 0.00")
        self.report_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.report_total_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #4caf50;")
        stats_layout.addWidget(self.report_total_label)
        
        self.report_count_label = QLabel("0 artículos vendidos")
        self.report_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.report_count_label.setStyleSheet("font-size: 16px; color: #888888;")
        stats_layout.addWidget(self.report_count_label)
        
        top_layout.addWidget(cal_wrapper)
        top_layout.addWidget(self.stats_card)
        
        top_layout.setStretch(0, 0) 
        top_layout.setStretch(1, 1) 
        
        reportes_layout.addWidget(top_container)
        
        lbl_desglose = QLabel("Desglose de productos:")
        lbl_desglose.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        reportes_layout.addWidget(lbl_desglose)
        
        self.report_table = QTableWidget()
        self.report_table.setObjectName("employee_table") 
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Platillo", "Cantidad Vendida"])
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.report_table.setColumnWidth(1, 150)
        
        btn_web_report = QPushButton("Ver Gráficas Detalladas (Web)")
        btn_web_report.setObjectName("blue_button") 
        btn_web_report.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_web_report.setFixedHeight(40)
        btn_web_report.clicked.connect(self.abrir_reportes_web)
        
        reportes_layout.addWidget(btn_web_report) 
        reportes_layout.addWidget(self.report_table)
        
        self.tab_widget.addTab(reportes_tab, "Reportes")

        # --- Tab Nómina ---
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

        # --- Conexiones Generales ---
        self.btn_add_employee.clicked.connect(self.add_employee)
        self.btn_edit_employee.clicked.connect(self.edit_employee)
        self.btn_delete_employee.clicked.connect(self.delete_employee)
        self.btn_format_sensor.clicked.connect(self.formatear_sensor)

        self.btn_add_table.clicked.connect(self.add_table)
        self.btn_remove_table.clicked.connect(self.remove_table)
        
        # Conexiones nuevas del Menú
        self.btn_add_cat.clicked.connect(self.agregar_categoria)
        self.btn_add_item.clicked.connect(self.agregar_platillo)
        self.btn_edit_item.clicked.connect(self.editar_platillo)
        self.btn_delete_item.clicked.connect(self.eliminar_elemento)
        self.btn_save_menu.clicked.connect(self.save_menu_data)
        
        self.calendar.selectionChanged.connect(self.mostrar_reporte_del_dia)
        
        self.btn_calculate_payroll.clicked.connect(self.calculate_payroll)
        self.btn_export_pdf.clicked.connect(self.export_payroll_pdf)
        self.btn_generate_random.clicked.connect(self.generate_random_attendance)
        self.payroll_table.itemSelectionChanged.connect(self.update_export_button_state)

        # ---------------------------------------------------------------------
        # IMPORTANTE: Cargar datos iniciales AL FINAL, cuando todos los widgets existen.
        # ---------------------------------------------------------------------
        self._load_initial_data()

    def abrir_reportes_web(self):
        url = "http://127.0.0.1:5000/reportes-web"
        QDesktopServices.openUrl(QUrl(url))
        print(f"Abriendo dashboard web: {url}")

    def _load_initial_data(self):
        logger.info("Cargando datos iniciales de AdminPage desde la BD...")
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
        dialog = EmployeeFormDialog(self, available_roles=self.available_roles, api_key=self.app_controller.API_KEY)
        if dialog.exec():
            data = dialog.get_data()
            if not data['id'] or not data['nombre']: return 
            
            if self.app_controller.data_manager.get_employee_by_id(data['id']):
                QMessageBox.warning(self, "Error", f"El ID '{data['id']}' ya existe.")
                return

            result = self.app_controller.agregar_empleado(data['id'], data['nombre'], data['rol'], data['fingerprint_id'])
            
            if result:
                print(f"✅ Empleado '{data['nombre']}' añadido con huella ID: {data['fingerprint_id']}")
                self.refresh_employee_table()
            else:
                QMessageBox.critical(self, "Error", "No se pudo añadir el empleado.")

    def edit_employee(self):
        current_row = self.employee_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione un empleado para editar.")
            return
        
        original_id_item = self.employee_table.item(current_row, 0)
        original_id = original_id_item.text()
        
        original_employee = self.app_controller.data_manager.get_employee_by_id(original_id)
        if not original_employee: return
        
        dialog = EmployeeFormDialog(self, employee_data=original_employee, available_roles=self.available_roles, api_key=self.app_controller.API_KEY)
        if dialog.exec():
            data = dialog.get_data()
            
            if data['id'] != original_id and self.app_controller.data_manager.get_employee_by_id(data['id']):
                QMessageBox.warning(self, "Error", f"El ID '{data['id']}' ya existe.")
                return

            self.app_controller.editar_empleado(original_id, data['id'], data['nombre'], data['rol'], data['fingerprint_id'])
            
            print(f"Empleado editado. Huella ID: {data['fingerprint_id']}")
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
                
            print(f"Empleado '{employee_name}' (ID: {employee_id}) eliminado de la BD.")
            
            self.refresh_employee_table()
            
        else:
            print("Operación cancelada.")
    
    # --- GESTIÓN DE MENÚ Y LÓGICA (NUEVO) ---

    def load_menu_data(self):
        self.menu_tree.clear() 
        
        try:
            menu_data = self.app_controller.data_manager.get_menu_with_categories()
            
            for categoria_data in menu_data.get("categorias", []):
                categoria_nombre = categoria_data.get("nombre", "Sin Categoría")
                parent_item = QTreeWidgetItem(self.menu_tree)
                parent_item.setText(0, categoria_nombre)
                parent_item.setData(0, Qt.ItemDataRole.UserRole, "categoria")
                parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable) # Categorías no seleccionables para edición simple
                
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

    def agregar_categoria(self):
        dialog = CategoryFormDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['nombre']: return
            
            try:
                self.app_controller.data_manager.execute(
                    "INSERT INTO menu_categorias (nombre, destino) VALUES (?, ?)",
                    (data['nombre'], data['destino'])
                )
                self.load_menu_data()
                QMessageBox.information(self, "Éxito", f"Categoría '{data['nombre']}' creada.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al crear categoría: {e}")

    def agregar_platillo(self):
        cats = self.app_controller.data_manager.fetchall("SELECT * FROM menu_categorias")
        if not cats:
            QMessageBox.warning(self, "Aviso", "Primero debes crear una categoría.")
            return

        dialog = MenuItemFormDialog(self, categories=cats)
        if dialog.exec():
            data = dialog.get_data()
            if not data['nombre']: return
            
            cat_id = next((c['id_categoria'] for c in cats if c['nombre'] == data['categoria_nombre']), None)
            
            import uuid
            new_id = str(uuid.uuid4())[:8] 

            final_img_name = ""
            if data['imagen_path']:
                try:
                    ext = os.path.splitext(data['imagen_path'])[1]
                    final_img_name = f"{new_id}{ext}"
                    dest_path = os.path.join(BASE_DIR, "assets", final_img_name)
                    shutil.copy(data['imagen_path'], dest_path)
                except Exception as e:
                    print(f"Error copiando imagen: {e}")

            try:
                self.app_controller.data_manager.execute(
                    """INSERT INTO menu_items 
                       (id_item, id_categoria, nombre, precio, descripcion, imagen, disponible)
                       VALUES (?, ?, ?, ?, ?, ?, 1)""",
                    (new_id, cat_id, data['nombre'], data['precio'], data['descripcion'], final_img_name)
                )
                self.load_menu_data()
                self._notify_server_config_change()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error BD: {e}")

    def editar_platillo(self, item=None):
        if not item:
            item = self.menu_tree.currentItem()
            
        if not item: 
            QMessageBox.warning(self, "Selección", "Selecciona un platillo para editar.")
            return

        widget = self.menu_tree.itemWidget(item, 0)
        if not isinstance(widget, PlatilloItemWidget):
            return 

        item_id = widget.item_id
        
        item_data = self.app_controller.data_manager.fetchone(
            "SELECT * FROM menu_items WHERE id_item = ?", (item_id,)
        )
        if not item_data: return
        
        cat_data = self.app_controller.data_manager.fetchone(
            "SELECT nombre FROM menu_categorias WHERE id_categoria = ?", (item_data['id_categoria'],)
        )
        item_data_dict = dict(item_data)
        item_data_dict['categoria_nombre'] = cat_data['nombre'] if cat_data else ""

        cats = self.app_controller.data_manager.fetchall("SELECT * FROM menu_categorias")
        
        dialog = MenuItemFormDialog(self, item_data=item_data_dict, categories=cats)
        if dialog.exec():
            new_data = dialog.get_data()
            
            new_cat_id = next((c['id_categoria'] for c in cats if c['nombre'] == new_data['categoria_nombre']), None)
            
            final_img_name = item_data['imagen']
            if new_data['imagen_path'] and new_data['imagen_path'] != item_data['imagen']:
                if os.path.isabs(new_data['imagen_path']):
                    try:
                        ext = os.path.splitext(new_data['imagen_path'])[1]
                        final_img_name = f"{item_id}_{int(datetime.datetime.now().timestamp())}{ext}"
                        dest_path = os.path.join(BASE_DIR, "assets", final_img_name)
                        shutil.copy(new_data['imagen_path'], dest_path)
                    except Exception as e:
                        print(f"Error copiando imagen: {e}")

            self.app_controller.data_manager.execute(
                """UPDATE menu_items 
                   SET nombre=?, precio=?, descripcion=?, id_categoria=?, imagen=? 
                   WHERE id_item=?""",
                (new_data['nombre'], new_data['precio'], new_data['descripcion'], new_cat_id, final_img_name, item_id)
            )
            
            self.load_menu_data()
            self._notify_server_config_change()
            QMessageBox.information(self, "Actualizado", "Platillo actualizado correctamente.")

    def eliminar_elemento(self):
        item = self.menu_tree.currentItem()
        if not item: return
        
        widget = self.menu_tree.itemWidget(item, 0)
        
        if isinstance(widget, PlatilloItemWidget):
            item_id = widget.item_id
            nombre_mostrar = "este platillo"
            
            try:
                dato_db = self.app_controller.data_manager.fetchone(
                    "SELECT nombre FROM menu_items WHERE id_item = ?", (item_id,)
                )
                if dato_db and 'nombre' in dato_db:
                    nombre_mostrar = dato_db['nombre']
            except Exception:
                pass 

            confirm = QMessageBox.question(self, "Eliminar Platillo", 
                f"¿Eliminar permanentemente '{nombre_mostrar}'?\nEsto no afectará reportes pasados.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                self.app_controller.data_manager.execute(
                    "DELETE FROM menu_items WHERE id_item = ?", (item_id,)
                )
                self.load_menu_data()
                self._notify_server_config_change()
        
        elif item.data(0, Qt.ItemDataRole.UserRole) == "categoria":
            cat_name = item.text(0)
            confirm = QMessageBox.warning(self, "Eliminar Categoría",
                f"¿Eliminar la categoría '{cat_name}'?\n\n¡CUIDADO! Esto eliminará TODOS los platillos dentro de ella.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if confirm == QMessageBox.StandardButton.Yes:
                cat = self.app_controller.data_manager.fetchone(
                    "SELECT id_categoria FROM menu_categorias WHERE nombre = ?", (cat_name,)
                )
                if cat:
                    self.app_controller.data_manager.execute(
                        "DELETE FROM menu_items WHERE id_categoria = ?", (cat['id_categoria'],)
                    )
                    self.app_controller.data_manager.execute(
                        "DELETE FROM menu_categorias WHERE id_categoria = ?", (cat['id_categoria'],)
                    )
                    self.load_menu_data()
                    self._notify_server_config_change()

    def save_menu_data(self):
        print("Guardando disponibilidad del menú...")
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
            
            logger.info(f"Disponibilidad actualizada ({len(updates_to_make)} items)")
            QMessageBox.information(self, "Éxito", "Disponibilidad actualizada.")
            self._notify_server_config_change()

        except Exception as e:
            logger.error(f"Error guardando disponibilidad: {e}")
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo actualizar:\n{e}")

    # --- REPORTES Y OTROS ---

    def mostrar_reporte_del_dia(self):
        selected_date = self.calendar.selectedDate().toPyDate()
        selected_date_str = selected_date.isoformat()
        
        logger.info(f"Generando reporte visual para {selected_date_str}")

        total_ventas, items_vendidos = self.app_controller.data_manager.get_sales_report(selected_date_str)
        
        total_items = sum(item["cantidad_total"] for item in items_vendidos)
        
        self.report_total_label.setText(f"C$ {total_ventas:,.2f}") 
        self.report_count_label.setText(f"{total_items} artículos vendidos")

        self.report_table.setRowCount(len(items_vendidos))
        for row, item in enumerate(items_vendidos):
            item_nombre = QTableWidgetItem(item["nombre"])
            item_cantidad = QTableWidgetItem(str(item["cantidad_total"]))
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.report_table.setItem(row, 0, item_nombre)
            self.report_table.setItem(row, 1, item_cantidad)
            
        logger.info(f"Reporte generado. Total: C${total_ventas:.2f}")


    def calculate_payroll(self):
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()

        start_date = start_date_q.toPyDate()
        end_date_inclusive = end_date_q.toPyDate()
        end_date_exclusive = end_date_q.toPyDate() + datetime.timedelta(days=1)

        print(f"Calculando nómina desde {start_date} hasta {end_date_inclusive}...")

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
        print(f"Nómina calculada y mostrada para {len(payroll_results)} empleados. Detalles diarios guardados para PDF.")


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

        print(f"Preparando PDF para {employee_name} (ID: {employee_id}) del {start_date} al {end_date}...")

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
                print(f"Advertencia: No se encontró el logo en {logo_path}")
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
            logger.info("Configuración guardada en config.json")
        except Exception as e:
            logger.critical(f"Error guardando config.json: {e}")
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
                logger.info("Notificación de configuración enviada al servidor.")
            else:
                logger.warning(f"Servidor rechazó la notificación de configuración. Código: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"No se pudo conectar con el servidor para notificar configuración: {e}")

    def formatear_sensor(self):
        confirm = QMessageBox.warning(self, 
                                    "PELIGRO: Formatear Sensor", 
                                    "¿Estás seguro? Esto borrará TODAS las huellas almacenadas en el sensor físico.\n\nLos empleados tendrán que registrar su huella de nuevo.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                    QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                api_key = self.app_controller.API_KEY
                
                api_url = "http://127.0.0.1:5000/api/biometric/start-clear"
                headers = {'X-API-KEY': api_key}
                
                response = requests.post(api_url, headers=headers, timeout=2)
                
                if response.status_code == 200:
                    QMessageBox.information(self, "Orden Enviada", "El sensor se formateará en los próximos segundos.")
                else:
                    QMessageBox.warning(self, "Error", f"El servidor no aceptó la orden. Código: {response.status_code}")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar con el servidor local:\n{str(e)}")