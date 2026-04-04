import os
import random
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QTableWidget, 
                             QHeaderView, QLineEdit, QDoubleSpinBox, QFormLayout, QMessageBox, QFileDialog, QTableWidgetItem, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from logger_setup import setup_logger

logger = setup_logger()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
                from PyQt6.QtWidgets import QListWidgetItem
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
                ext = os.path.splitext(self.image_path)[1]
                final_img = f"combo_{random.randint(1000,9999)}{ext}"
                dest = os.path.join(BASE_DIR, "assets", final_img)
                shutil.copy(self.image_path, dest)
            except Exception as e:
                logger.error(f"Error copiando imagen de combo: {e}")
        self.app_controller.data_manager.create_combo_item(name, price, full_desc, final_img)
        self.combo_creado.emit()
        QMessageBox.information(self, "¡Listo!", f"El '{name}' ha sido creado en la categoría Promociones.")
        self.selected_items = {}
        self.inp_name.clear()
        self.inp_price.setValue(0)
        self.image_path = None
        self.lbl_img_status.setText("Sin Imagen")
        self.render_target_list()