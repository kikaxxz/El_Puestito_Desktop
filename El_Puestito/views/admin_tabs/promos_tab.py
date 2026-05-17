import os
import random
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QTableWidget, QHeaderView, QLineEdit, 
                             QDoubleSpinBox, QFormLayout, QMessageBox, QFileDialog, 
                             QTableWidgetItem, QAbstractItemView, QSpinBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
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
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        lbl_title1 = QLabel("1. Selecciona Productos:")
        font_title = QFont()
        font_title.setPointSize(12)
        font_title.setBold(True)
        lbl_title1.setFont(font_title)
        left_layout.addWidget(lbl_title1)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar producto...")
        self.search_bar.setStyleSheet("background: #2b2b2b; color: white; padding: 8px; border-radius: 5px; border: 1px solid #444;")
        self.search_bar.textChanged.connect(self.filter_products)
        left_layout.addWidget(self.search_bar)
        
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.source_list.setStyleSheet("background: #2b2b2b; color: white; border-radius: 5px; padding: 5px;")
        self.source_list.itemDoubleClicked.connect(self.add_item_to_combo)
        left_layout.addWidget(self.source_list)
        
        btn_add = QPushButton("Añadir al Combo >>")
        btn_add.setObjectName("blue_button") 
        btn_add.setMinimumHeight(40)
        btn_add.clicked.connect(self.add_item_to_combo)
        left_layout.addWidget(btn_add)
        
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        
        lbl_title2 = QLabel("2. Contenido del Combo:")
        lbl_title2.setFont(font_title)
        right_layout.addWidget(lbl_title2)
        
        self.target_list = QTableWidget()
        self.target_list.setColumnCount(3)
        self.target_list.setHorizontalHeaderLabels(["Cant.", "Producto", "Quitar"])
        self.target_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.target_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.target_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.target_list.setAlternatingRowColors(True)
        self.target_list.setShowGrid(False)
        self.target_list.setStyleSheet("""
            QTableWidget { background: #1e1e24; color: white; border-radius: 5px; border: 1px solid #444; }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section { background-color: #2b2b2b; color: white; padding: 5px; border: none; font-weight: bold; }
        """)
        right_layout.addWidget(self.target_list)
        
        details_group = QGroupBox("Detalles de la Promoción")
        details_group.setStyleSheet("""
            QGroupBox { color: white; font-weight: bold; border: 1px solid #555; border-radius: 5px; margin-top: 10px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
        """)
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(15, 20, 15, 15)
        form_layout.setSpacing(10)
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Ej: Combo Alitas + Cerveza")
        self.inp_name.setStyleSheet("padding: 5px; border-radius: 3px; background: #2b2b2b; color: white; border: 1px solid #444;")
        
        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 99999)
        self.inp_price.setPrefix("C$ ")
        self.inp_price.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.inp_price.setStyleSheet("padding: 5px; border-radius: 3px; background: #2b2b2b; color: white; border: 1px solid #444;")
        
        self.lbl_img_status = QLabel("Sin Imagen")
        self.lbl_img_status.setStyleSheet("color: #aaa; font-style: italic;")
        
        self.btn_img = QPushButton("Cargar Foto...")
        self.btn_img.setStyleSheet("background-color: #444; color: white; padding: 8px; border-radius: 4px;")
        self.btn_img.clicked.connect(self.select_image)
        
        form_layout.addRow("Nombre Combo:", self.inp_name)
        form_layout.addRow("Precio Final:", self.inp_price)
        form_layout.addRow(self.lbl_img_status, self.btn_img)
        
        details_group.setLayout(form_layout)
        right_layout.addWidget(details_group)
        
        btn_create = QPushButton("CREAR PROMOCIÓN")
        btn_create.setObjectName("orange_button")
        btn_create.setMinimumHeight(50)
        right_layout.addWidget(btn_create)
        btn_create.clicked.connect(self.save_combo)
        
        main_layout.addLayout(left_layout, 4)
        main_layout.addLayout(right_layout, 5)
        
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

    def filter_products(self, text):
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

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

    def update_qty(self, item_id, new_qty):
        if new_qty == 0:
            self.remove_item(item_id)
        elif item_id in self.selected_items:
            self.selected_items[item_id]['qty'] = new_qty
        
    def remove_item(self, item_id):
        if item_id in self.selected_items:
            del self.selected_items[item_id]
            self.render_target_list()

    def render_target_list(self):
        self.target_list.setRowCount(0)
        self.target_list.setRowCount(len(self.selected_items))
        for row, (uid, data) in enumerate(self.selected_items.items()):
            spin_qty = QSpinBox()
            spin_qty.setRange(0, 99)
            spin_qty.setValue(data['qty'])
            spin_qty.setStyleSheet("background: #2b2b2b; color: white; border: none;")
            spin_qty.valueChanged.connect(lambda val, x=uid: self.update_qty(x, val))
            
            name_item = QTableWidgetItem(data['nombre'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            btn_del = QPushButton("✕")
            btn_del.setStyleSheet("color: #ff4c4c; font-weight: bold; border: none; font-size: 14px;")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda _, x=uid: self.remove_item(x))
            
            self.target_list.setCellWidget(row, 0, spin_qty)
            self.target_list.setItem(row, 1, name_item)
            self.target_list.setCellWidget(row, 2, btn_del)

    def select_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Foto", "", "Imágenes (*.png *.jpg *.jpeg)")
        if file_name:
            self.image_path = file_name
            self.lbl_img_status.setText(os.path.basename(file_name))
            self.lbl_img_status.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.btn_img.setText("Cambiar Foto...")

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
        self.lbl_img_status.setStyleSheet("color: #aaa; font-style: italic;")
        self.btn_img.setText("Cargar Foto...")
        self.render_target_list()