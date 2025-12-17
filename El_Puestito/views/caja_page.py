import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QMessageBox,
    QScrollArea, QGridLayout, QButtonGroup, QFrame, QScroller
)
from PyQt6.QtCore import Qt, QSize

class MesaCard(QPushButton):
    """Botón personalizado que representa una mesa en la caja."""
    def __init__(self, text, mesa_key, parent=None):
        super().__init__(text, parent)
        self.mesa_key = mesa_key
        self.setCheckable(True) 
        self.setFixedSize(125, 80) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("mesa_card")
        
        self.setStyleSheet("""
            QPushButton#mesa_card {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton#mesa_card:checked {
                background-color: rgba(247, 102, 6, 0.2); /* Naranja translúcido */
                border: 2px solid #f76606; /* Borde Naranja Neón */
                color: #ffffff;
            }
            QPushButton#mesa_card:hover:!checked {
                background-color: #383838;
                border: 1px solid #555;
            }
        """)

class CajaPage(QWidget):

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.ordenes_activas = {}
        self.mesa_actual = None  
        
        self.mesas_button_group = QButtonGroup(self)
        self.mesas_button_group.setExclusive(True)
        self.mesas_button_group.buttonClicked.connect(self.al_seleccionar_mesa)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(320) 
        left_layout.setContentsMargins(15, 15, 15, 15)
        
        mesas_title = QLabel("Mesas Activas")
        mesas_title.setObjectName("section_title")
        
        self.scroll_mesas = QScrollArea()
        self.scroll_mesas.setWidgetResizable(True)
        self.scroll_mesas.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_mesas.setStyleSheet("background: transparent; border: none;")
        
        QScroller.grabGesture(self.scroll_mesas.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        QScroller.grabGesture(self.scroll_mesas.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.mesas_container = QWidget()
        self.mesas_grid = QGridLayout(self.mesas_container)
        self.mesas_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mesas_grid.setSpacing(10)
        self.mesas_grid.setContentsMargins(0,0,0,0)
        
        self.scroll_mesas.setWidget(self.mesas_container)
        
        left_layout.addWidget(mesas_title)
        left_layout.addWidget(self.scroll_mesas)

        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #1e1e24; border-left: 1px solid #333;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)
        
        cuenta_title = QLabel("Detalle de la Cuenta")
        cuenta_title.setObjectName("section_title")
        
        self.tabla_cuenta = QTableWidget()
        self.tabla_cuenta.setObjectName("tabla_cuenta_caja")
        self.tabla_cuenta.setColumnCount(4)
        self.tabla_cuenta.setHorizontalHeaderLabels(["Cant.", "Producto", "P. Unit", "Subtotal"])
        self.tabla_cuenta.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_cuenta.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_cuenta.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_cuenta.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        QScroller.grabGesture(self.tabla_cuenta.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        QScroller.grabGesture(self.tabla_cuenta.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        total_frame = QFrame()
        total_frame.setStyleSheet("""
            background-color: #2b2b2b; 
            border-radius: 12px; 
            padding: 10px;
            margin-top: 10px;
        """)
        total_layout = QHBoxLayout(total_frame)
        
        lbl_total_text = QLabel("TOTAL A PAGAR:")
        lbl_total_text.setStyleSheet("color: #aaa; font-weight: bold; font-size: 14px;")
        
        self.total_label = QLabel("C$ 0.00")
        self.total_label.setStyleSheet("color: #00d26a; font-weight: 800; font-size: 28px;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        total_layout.addWidget(lbl_total_text)
        total_layout.addWidget(self.total_label)
        
        self.cobrar_button = QPushButton("Cobrar y Cerrar Mesa")
        self.cobrar_button.setObjectName("orange_button")
        self.cobrar_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cobrar_button.setFixedHeight(50)
        self.cobrar_button.setStyleSheet("""
            QPushButton {
                background-color: #f76606; 
                color: white;
                font-weight: bold;
                font-size: 18px;
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff7b24; 
            }
            QPushButton:pressed {
                background-color: #d65500; 
            }
        """)
        right_layout.addWidget(cuenta_title)
        right_layout.addWidget(self.tabla_cuenta)
        right_layout.addWidget(total_frame)
        right_layout.addWidget(self.cobrar_button)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.cobrar_button.clicked.connect(self.cobrar_cuenta)
        
        self.load_active_orders()
        self.app_controller.ordenes_actualizadas.connect(self.load_active_orders)

    def load_active_orders(self):
        """Recarga las mesas y reconstruye el Grid."""
        self.mesas_container.setUpdatesEnabled(False)
        try:
            mesa_previa = self.mesa_actual
            
            while self.mesas_grid.count():
                item = self.mesas_grid.takeAt(0)
                widget = item.widget()
                if widget:
                    self.mesas_button_group.removeButton(widget) 
                    widget.deleteLater()
            
            self.ordenes_activas = {}
            
            self.ordenes_activas = self.app_controller.data_manager.get_active_orders_caja()
            sorted_keys = sorted(self.ordenes_activas.keys())

            col = 0
            row = 0
            
            for mesa_key in sorted_keys:
                orden = self.ordenes_activas[mesa_key]
                if not orden['items']: continue

                display_text = self._formatear_nombre_mesa(mesa_key)
                
                card = MesaCard(display_text, mesa_key)
                self.mesas_button_group.addButton(card) 
                self.mesas_grid.addWidget(card, row, col)
                
                if mesa_key == mesa_previa:
                    card.setChecked(True)
                    self._llenar_tabla_detalle(orden)
                
                col += 1
                if col > 1: 
                    col = 0
                    row += 1
            
            if mesa_previa and mesa_previa not in self.ordenes_activas:
                self._limpiar_tabla()
                self.mesa_actual = None

        except Exception as e:
            print(f"Error cargando órdenes: {e}")
            self.ordenes_activas = {}
        finally:
            self.mesas_container.setUpdatesEnabled(True)

    def _formatear_nombre_mesa(self, mesa_key):
        """Helper para que el texto del botón se vea bonito."""
        base_key = mesa_key
        suffix = ""
        
        if "-" in mesa_key:
            try:
                parts = mesa_key.rsplit('-', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    base_key = parts[0]
                    suffix = f"\n(Sub {parts[1]})"
            except: pass 

        prefix = "Grupo" if "+" in base_key else "Mesa"
        return f"{prefix} {base_key}{suffix}"

    def al_seleccionar_mesa(self, button):
        """Slot conectado al Click del ButtonGroup."""
        if not button: return
        
        mesa_key = button.mesa_key
        self.mesa_actual = mesa_key
        
        if mesa_key in self.ordenes_activas:
            self._llenar_tabla_detalle(self.ordenes_activas[mesa_key])
        else:
            self._limpiar_tabla()

    def _llenar_tabla_detalle(self, orden):
        """Llena la tabla derecha."""
        self.tabla_cuenta.setUpdatesEnabled(False)
        items = orden.get('items', [])
        self.tabla_cuenta.setRowCount(len(items))
        
        total = 0.0
        for row, platillo in enumerate(items):
            cantidad = platillo['cantidad']
            nombre = platillo['nombre']
            precio = platillo['precio_unitario']
            subtotal = cantidad * precio
            total += subtotal
            
            item_qty = QTableWidgetItem(str(cantidad))
            item_qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_name = QTableWidgetItem(nombre)
            
            item_price = QTableWidgetItem(f"{precio:.2f}")
            item_price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            item_sub = QTableWidgetItem(f"{subtotal:.2f}")
            item_sub.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            self.tabla_cuenta.setItem(row, 0, item_qty)
            self.tabla_cuenta.setItem(row, 1, item_name)
            self.tabla_cuenta.setItem(row, 2, item_price)
            self.tabla_cuenta.setItem(row, 3, item_sub)
            
        self.total_label.setText(f"C$ {total:,.2f}")
        self.tabla_cuenta.setUpdatesEnabled(True)

    def cobrar_cuenta(self):
        btn_seleccionado = self.mesas_button_group.checkedButton()
        
        if not btn_seleccionado: 
            QMessageBox.warning(self, "Acción no válida", "Por favor, seleccione una mesa para cobrar.")
            return
        
        mesa_key = btn_seleccionado.mesa_key
        texto_mesa = btn_seleccionado.text().replace('\n', ' ')
        
        confirm = QMessageBox.question(
            self, "Confirmar Cobro", 
            f"¿Desea cerrar y cobrar la {texto_mesa}?\nTotal: {self.total_label.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            exito = self.app_controller.cobrar_cuenta(mesa_key)
            
            if exito:
                self._limpiar_tabla()
                self.mesa_actual = None
            else:
                QMessageBox.critical(self, "Error", "No se pudo cerrar la cuenta en la base de datos.")

    def _limpiar_tabla(self):
        self.tabla_cuenta.setRowCount(0)
        self.total_label.setText("C$ 0.00")
        btn = self.mesas_button_group.checkedButton()
        if btn:
            self.mesas_button_group.setExclusive(False)
            btn.setChecked(False)
            self.mesas_button_group.setExclusive(True)