import os
import shutil
import uuid
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, 
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, 
                             QTextEdit, QFileDialog, QTreeWidgetItemIterator)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from widgets.platillo_item import PlatilloItemWidget
from logger_setup import setup_logger

logger = setup_logger()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CategoryFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Categoria")
        self.setFixedSize(300, 150)
        layout = QFormLayout(self)
        self.inp_nombre = QLineEdit()
        self.combo_destino = QComboBox()
        self.combo_destino.addItems(["cocina", "barra"])
        layout.addRow("Nombre Categoria:", self.inp_nombre)
        layout.addRow("Destino Impresion:", self.combo_destino)
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
        self.inp_desc.setPlaceholderText("Ingredientes, alergenos, detalles...")
        self.inp_desc.setMaximumHeight(80)
        if item_data: self.inp_desc.setText(item_data.get('descripcion', ''))
        self.inp_desc.setObjectName("dialog_input")
        lbl_nombre = QLabel("Nombre:")
        lbl_nombre.setStyleSheet("font-weight: bold; color: #ccc;") 
        lbl_precio = QLabel("Precio:")
        lbl_precio.setStyleSheet("font-weight: bold; color: #ccc;")
        lbl_cat = QLabel("Categoria:")
        lbl_cat.setStyleSheet("font-weight: bold; color: #ccc;")
        lbl_desc = QLabel("Descripcion:")
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
        img_layout.addWidget(QLabel("Fotografia:"))
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
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Imagenes (*.png *.jpg *.jpeg)")
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

class MenuTab(QWidget):
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.setup_ui()
        self.load_menu_data()

    def setup_ui(self):
        menu_layout = QVBoxLayout(self)
        menu_layout.setContentsMargins(15, 15, 15, 15)
        menu_layout.setSpacing(10)
        menu_controls = QHBoxLayout()
        self.btn_add_cat = QPushButton("Nueva Categoria")
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
        self.menu_tree = QTreeWidget()
        self.menu_tree.setObjectName("menu_tree")
        self.menu_tree.setColumnCount(1) 
        self.menu_tree.setHeaderLabels(["Platillo / Categoria"])
        menu_header = self.menu_tree.header()
        menu_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.menu_tree.setStyleSheet("QTreeWidget::item { height: 60px; }")
        menu_layout.addWidget(self.menu_tree)
        self.btn_save_menu = QPushButton("Guardar Disponibilidad (ON/OFF)")
        menu_layout.addWidget(self.btn_save_menu)
        self.btn_add_cat.clicked.connect(self.agregar_categoria)
        self.btn_add_item.clicked.connect(self.agregar_platillo)
        self.btn_edit_item.clicked.connect(self.editar_platillo)
        self.btn_delete_item.clicked.connect(self.eliminar_elemento)
        self.btn_save_menu.clicked.connect(self.save_menu_data)
        self.menu_tree.itemDoubleClicked.connect(self.editar_platillo)

    def load_menu_data(self):
        self.menu_tree.clear() 
        try:
            menu_data = self.app_controller.data_manager.get_menu_with_categories()
            for categoria_data in menu_data.get("categorias", []):
                categoria_nombre = categoria_data.get("nombre", "Sin Categoria")
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
            logger.error(f"Error inesperado al cargar menu desde BD: {e}")
            QMessageBox.critical(self, "Error de Menu", f"No se pudo cargar el menu desde la base de datos:\n{e}")

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
                QMessageBox.information(self, "Exito", f"Categoria '{data['nombre']}' creada.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al crear categoria: {e}")

    def agregar_platillo(self):
        cats = self.app_controller.data_manager.fetchall("SELECT * FROM menu_categorias")
        if not cats:
            QMessageBox.warning(self, "Aviso", "Primero debes crear una categoria.")
            return
        dialog = MenuItemFormDialog(self, categories=cats)
        if dialog.exec():
            data = dialog.get_data()
            if not data['nombre']: return
            cat_id = next((c['id_categoria'] for c in cats if c['nombre'] == data['categoria_nombre']), None)
            new_id = str(uuid.uuid4())[:8] 
            final_img_name = ""
            if data['imagen_path']:
                try:
                    ext = os.path.splitext(data['imagen_path'])[1]
                    final_img_name = f"{new_id}{ext}"
                    dest_path = os.path.join(BASE_DIR, "assets", final_img_name)
                    shutil.copy(data['imagen_path'], dest_path)
                except Exception as e:
                    logger.error(f"Error copiando imagen: {e}")
            try:
                self.app_controller.data_manager.execute(
                    "INSERT INTO menu_items (id_item, id_categoria, nombre, precio, descripcion, imagen, disponible) VALUES (?, ?, ?, ?, ?, ?, 1)",
                    (new_id, cat_id, data['nombre'], data['precio'], data['descripcion'], final_img_name)
                )
                self.load_menu_data()
                self.app_controller.notify_server_config_change()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error BD: {e}")

    def editar_platillo(self, item=None):
        if not item:
            item = self.menu_tree.currentItem()
        if not item: 
            QMessageBox.warning(self, "Seleccion", "Selecciona un platillo para editar.")
            return
        widget = self.menu_tree.itemWidget(item, 0)
        if not isinstance(widget, PlatilloItemWidget):
            return 
        item_id = widget.item_id
        item_data = self.app_controller.data_manager.fetchone("SELECT * FROM menu_items WHERE id_item = ?", (item_id,))
        if not item_data: return
        cat_data = self.app_controller.data_manager.fetchone("SELECT nombre FROM menu_categorias WHERE id_categoria = ?", (item_data['id_categoria'],))
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
                        logger.error(f"Error copiando imagen: {e}")
            self.app_controller.data_manager.execute(
                "UPDATE menu_items SET nombre=?, precio=?, descripcion=?, id_categoria=?, imagen=? WHERE id_item=?",
                (new_data['nombre'], new_data['precio'], new_data['descripcion'], new_cat_id, final_img_name, item_id)
            )
            self.load_menu_data()
            self.app_controller.notify_server_config_change()
            QMessageBox.information(self, "Actualizado", "Platillo actualizado correctamente.")

    def eliminar_elemento(self):
        item = self.menu_tree.currentItem()
        if not item: return
        widget = self.menu_tree.itemWidget(item, 0)
        if isinstance(widget, PlatilloItemWidget):
            item_id = widget.item_id
            nombre_mostrar = "este platillo"
            try:
                dato_db = self.app_controller.data_manager.fetchone("SELECT nombre FROM menu_items WHERE id_item = ?", (item_id,))
                if dato_db and 'nombre' in dato_db:
                    nombre_mostrar = dato_db['nombre']
            except Exception:
                pass 
            confirm = QMessageBox.question(self, "Eliminar Platillo", f"¿Eliminar permanentemente '{nombre_mostrar}'?\nEsto no afectara reportes pasados.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.app_controller.data_manager.execute("DELETE FROM menu_items WHERE id_item = ?", (item_id,))
                self.load_menu_data()
                self.app_controller.notify_server_config_change()
        elif item.data(0, Qt.ItemDataRole.UserRole) == "categoria":
            cat_name = item.text(0)
            confirm = QMessageBox.warning(self, "Eliminar Categoria", f"¿Eliminar la categoria '{cat_name}'?\n\nCUIDADO Esto eliminara TODOS los platillos dentro de ella.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                cat = self.app_controller.data_manager.fetchone("SELECT id_categoria FROM menu_categorias WHERE nombre = ?", (cat_name,))
                if cat:
                    self.app_controller.data_manager.execute("DELETE FROM menu_items WHERE id_categoria = ?", (cat['id_categoria'],))
                    self.app_controller.data_manager.execute("DELETE FROM menu_categorias WHERE id_categoria = ?", (cat['id_categoria'],))
                    self.load_menu_data()
                    self.app_controller.notify_server_config_change()

    def save_menu_data(self):
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
            QMessageBox.information(self, "Exito", "Disponibilidad actualizada.")
            self.app_controller.notify_server_config_change()
        except Exception as e:
            logger.error(f"Error guardando disponibilidad: {e}")
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo actualizar:\n{e}")