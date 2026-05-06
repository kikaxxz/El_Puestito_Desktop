import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QMessageBox,
    QScrollArea, QGridLayout, QButtonGroup, QFrame, QScroller
)
from PyQt6.QtCore import Qt, QSize
from logger_setup import setup_logger

logger = setup_logger()

class MesaCard(QPushButton):
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
                background-color: rgba(247, 102, 6, 0.2);
                border: 2px solid #f76606;
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
        self.botones_mesas = {}
        
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
        
        buttons_layout = QHBoxLayout()
        
        self.btn_abrir_cajon = QPushButton("Abrir Cajon")
        self.btn_abrir_cajon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_cajon.setFixedHeight(50)
        self.btn_abrir_cajon.setStyleSheet("""
            QPushButton {
                background-color: #383838; 
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 12px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background-color: #4d4d4d; 
            }
            QPushButton:pressed {
                background-color: #2b2b2b; 
            }
        """)

        self.btn_imprimir_proforma = QPushButton("Imprimir Proforma")
        self.btn_imprimir_proforma.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_imprimir_proforma.setFixedHeight(50)
        self.btn_imprimir_proforma.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b; 
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 12px;
                border: 1px solid #777;
            }
            QPushButton:hover {
                background-color: #444; 
            }
            QPushButton:pressed {
                background-color: #1a1a1a; 
            }
        """)

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
        
        buttons_layout.addWidget(self.btn_abrir_cajon)
        buttons_layout.addWidget(self.btn_imprimir_proforma)
        buttons_layout.addWidget(self.cobrar_button)

        right_layout.addWidget(cuenta_title)
        right_layout.addWidget(self.tabla_cuenta)
        right_layout.addWidget(total_frame)
        right_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.cobrar_button.clicked.connect(self.cobrar_cuenta)
        self.btn_abrir_cajon.clicked.connect(self.abrir_cajon_manual)
        self.btn_imprimir_proforma.clicked.connect(self.imprimir_proforma)
        
        self.load_active_orders()
        self.app_controller.ordenes_actualizadas.connect(self.load_active_orders)

    def load_active_orders(self):
        self.mesas_container.setUpdatesEnabled(False)
        try:
            mesa_previa = self.mesa_actual
            
            nuevas_ordenes = self.app_controller.data_manager.get_active_orders_caja()
            
            ids_bd = set(nuevas_ordenes.keys())
            ids_pantalla = set(self.botones_mesas.keys())
            
            a_borrar = ids_pantalla - ids_bd
            for key in a_borrar:
                btn = self.botones_mesas.pop(key)
                self.mesas_button_group.removeButton(btn)
                btn.deleteLater()
            
            a_agregar = ids_bd - ids_pantalla
            for key in a_agregar:
                display_text = self._formatear_nombre_mesa(key)
                btn = MesaCard(display_text, key)
                self.mesas_button_group.addButton(btn)
                self.botones_mesas[key] = btn
            
            while self.mesas_grid.count():
                item = self.mesas_grid.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            
            sorted_keys = sorted(self.botones_mesas.keys())
            col = 0
            row = 0
            for key in sorted_keys:
                self.mesas_grid.addWidget(self.botones_mesas[key], row, col)
                col += 1
                if col > 1:
                    col = 0
                    row += 1
                    
            self.ordenes_activas = nuevas_ordenes
            
            if mesa_previa and mesa_previa in self.ordenes_activas:
                self.botones_mesas[mesa_previa].setChecked(True)
                self._llenar_tabla_detalle(self.ordenes_activas[mesa_previa])
            else:
                self._limpiar_tabla()
                self.mesa_actual = None

        except Exception as e:
            logger.error(f"Error cargando ordenes: {e}")
            self.ordenes_activas = {}
        finally:
            self.mesas_container.setUpdatesEnabled(True)

    def _formatear_nombre_mesa(self, mesa_key):
        base_key = mesa_key
        suffix = ""
        
        if "-" in mesa_key:
            try:
                parts = mesa_key.rsplit('-', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    base_key = parts[0]
                    suffix = f"\n(Sub {parts[1]})"
            except Exception as e: 
                logger.warning(f"Error al formatear nombre: {e}")

        prefix = "Grupo" if "+" in base_key else "Mesa"
        return f"{prefix} {base_key}{suffix}"

    def al_seleccionar_mesa(self, button):
        if not button: return
        
        mesa_key = button.mesa_key
        self.mesa_actual = mesa_key
        
        if mesa_key in self.ordenes_activas:
            self._llenar_tabla_detalle(self.ordenes_activas[mesa_key])
        else:
            self._limpiar_tabla()

    def _llenar_tabla_detalle(self, orden):
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

    def _preparar_datos_orden(self, mesa_key):
        orden = self.ordenes_activas.get(mesa_key)
        if not orden:
            return None
            
        items = orden.get('items', [])
        total = sum(item['cantidad'] * item['precio_unitario'] for item in items)
        
        return {
            'items': items,
            'total': total
        }

    def imprimir_proforma(self):
        btn_seleccionado = self.mesas_button_group.checkedButton()
        
        if not btn_seleccionado:
            QMessageBox.warning(self, "Accion no valida", "Por favor, seleccione una mesa.")
            return
            
        mesa_key = btn_seleccionado.mesa_key
        order_data = self._preparar_datos_orden(mesa_key)
        
        if not order_data:
            return
            
        if hasattr(self.app_controller, 'printer_service'):
            exito = self.app_controller.printer_service.print_receipt(order_data, is_proforma=True)
            if exito:
                self.app_controller.registrar_impresion_proforma(mesa_key)
                QMessageBox.information(self, "Impresion", "La proforma ha sido enviada a la impresora.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo imprimir la proforma. Verifique la conexion de la impresora.")
        else:
            logger.error("PrinterService no esta disponible en AppController.")

    def cobrar_cuenta(self):
        btn_seleccionado = self.mesas_button_group.checkedButton()
        
        if not btn_seleccionado: 
            QMessageBox.warning(self, "Accion no valida", "Por favor, seleccione una mesa para cobrar.")
            return
        
        mesa_key = btn_seleccionado.mesa_key
        texto_mesa = btn_seleccionado.text().replace('\n', ' ')
        
        confirm = QMessageBox.question(
            self, "Confirmar Cobro", 
            f"¿Desea cerrar y cobrar la {texto_mesa}?\nTotal: {self.total_label.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            order_data = self._preparar_datos_orden(mesa_key)
            exito = self.app_controller.cobrar_cuenta(mesa_key, order_data)
            
            if exito:
                self._limpiar_tabla()
                self.mesa_actual = None
            else:
                QMessageBox.critical(self, "Error", "No se pudo cerrar la cuenta en la base de datos.")

    def abrir_cajon_manual(self):
        if hasattr(self.app_controller, 'printer_service'):
            exito = self.app_controller.printer_service.open_cash_drawer()
            if not exito:
                logger.warning("Intento de apertura manual fallido o impresora no disponible.")

    def _limpiar_tabla(self):
        self.tabla_cuenta.setRowCount(0)
        self.total_label.setText("C$ 0.00")
        btn = self.mesas_button_group.checkedButton()
        if btn:
            self.mesas_button_group.setExclusive(False)
            btn.setChecked(False)
            self.mesas_button_group.setExclusive(True)