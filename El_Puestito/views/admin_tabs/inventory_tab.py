import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QGroupBox, QFormLayout, 
    QLineEdit, QSpinBox, QCheckBox, QComboBox, QMessageBox, QFrame,
    QInputDialog
)
from PyQt6.QtCore import Qt
from logger_setup import setup_logger

logger = setup_logger()

class InventoryTab(QWidget):
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.menu_items_map = {} 
        self.setup_ui()
        self.load_inventory_data()
        self.load_menu_items_reference()
        self.app_controller.ordenes_actualizadas.connect(self.load_inventory_data)
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # Sección: Formulario para agregar/editar
        form_group = QGroupBox("Gestión de Insumos")
        form_layout = QHBoxLayout()
        
        inner_form = QFormLayout()
        self.input_nombre = QLineEdit()
        self.input_cantidad = QSpinBox()
        self.input_cantidad.setRange(0, 10000)
        
        self.check_auto = QCheckBox("Descuento Automático")
        self.combo_menu = QComboBox()
        self.combo_menu.addItem("No vincular", None)
        self.combo_menu.setEnabled(False)

        self.check_auto.toggled.connect(self.combo_menu.setEnabled)

        inner_form.addRow("Nombre Insumo:", self.input_nombre)
        inner_form.addRow("Stock Inicial:", self.input_cantidad)
        inner_form.addRow(self.check_auto)
        inner_form.addRow("Vincular a Menú:", self.combo_menu)
        
        form_layout.addLayout(inner_form)

        btn_layout = QVBoxLayout()
        self.btn_add = QPushButton("Añadir al Inventario")
        self.btn_add.setObjectName("orange_button")
        self.btn_add.clicked.connect(self.handle_add_item)
        
        self.btn_refresh = QPushButton("Actualizar Lista")
        self.btn_refresh.clicked.connect(self.load_inventory_data)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addStretch()
        
        form_layout.addLayout(btn_layout)
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # Sección: Tabla de Inventario
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Insumo", "Cantidad", "Modo", "Vínculo Menú"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        main_layout.addWidget(self.table)

        # Botones de acción sobre la tabla
        actions_layout = QHBoxLayout()
        
        self.btn_add_stock = QPushButton("Sumar Stock")
        self.btn_add_stock.setStyleSheet("background-color: #32d74b; color: black; font-weight: bold;")
        self.btn_add_stock.clicked.connect(self.handle_add_stock)

        self.btn_delete = QPushButton("Eliminar Seleccionado")
        self.btn_delete.setStyleSheet("background-color: #ff453a; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self.handle_delete_item)
        
        actions_layout.addWidget(self.btn_add_stock)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_delete)
        main_layout.addLayout(actions_layout)

    def load_menu_items_reference(self):
        try:
            menu_data = self.app_controller.data_manager.get_menu_with_categories()
            self.combo_menu.clear()
            self.combo_menu.addItem("No vincular", None)
            
            for cat in menu_data.get("categorias", []):
                for item in cat.get("items", []):
                    nombre = item.get("nombre")
                    id_item = item.get("id_item")
                    self.combo_menu.addItem(f"{cat['nombre']} - {nombre}", id_item)
        except Exception as e:
            logger.error(f"Error cargando items de referencia: {e}")

    def load_inventory_data(self):
        try:
            items = self.app_controller.get_inventario()
            self.table.setRowCount(0)
            for i, row in enumerate(items):
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id_inventario'])))
                self.table.setItem(i, 1, QTableWidgetItem(row['nombre']))
                
                qty_item = QTableWidgetItem(str(row['cantidad']))
                if row['cantidad'] < 10: # Alerta visual de stock bajo
                    qty_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(i, 2, qty_item)
                
                modo = "Automático" if row['es_automatico'] else "Manual"
                self.table.setItem(i, 3, QTableWidgetItem(modo))
                self.table.setItem(i, 4, QTableWidgetItem(row['nombre_menu'] or "N/A"))
        except Exception as e:
            logger.error(f"Error cargando tabla de inventario: {e}")

    def handle_add_item(self):
        nombre = self.input_nombre.text().strip()
        cantidad = self.input_cantidad.value()
        es_auto = 1 if self.check_auto.isChecked() else 0
        id_menu = self.combo_menu.currentData()

        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return

        if self.app_controller.agregar_al_inventario(nombre, cantidad, es_auto, id_menu):
            self.load_inventory_data()
            self.input_nombre.clear()
            self.input_cantidad.setValue(0)
        else:
            QMessageBox.critical(self, "Error", "No se pudo agregar. Verifique que el nombre no esté repetido.")

    def handle_delete_item(self):
        current_row = self.table.currentRow()
        if current_row < 0: return
        
        id_inv = self.table.item(current_row, 0).text()
        nombre = self.table.item(current_row, 1).text()
        
        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar '{nombre}' del inventario?")
        if confirm == QMessageBox.StandardButton.Yes:
            if self.app_controller.eliminar_del_inventario(id_inv):
                self.load_inventory_data()

    def handle_add_stock(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Atención", "Seleccione un insumo de la tabla primero.")
            return

        id_inv = self.table.item(current_row, 0).text()
        nombre = self.table.item(current_row, 1).text()
        cantidad_actual = int(self.table.item(current_row, 2).text())

        cantidad_sumar, ok = QInputDialog.getInt(
            self, 
            "Sumar Stock", 
            f"Unidades de '{nombre}' a ingresar:", 
            0, 0, 10000, 1
        )

        if ok and cantidad_sumar > 0:
            nueva_cantidad = cantidad_actual + cantidad_sumar
            if self.app_controller.actualizar_stock(id_inv, nueva_cantidad):
                self.load_inventory_data()