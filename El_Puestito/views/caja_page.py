import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class CajaPage(QWidget):

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.ordenes_activas = {}
        self.mesa_actual = None  
        
        main_layout = QHBoxLayout(self)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)
        
        mesas_title = QLabel("Mesas con Órdenes Abiertas")
        mesas_title.setObjectName("section_title")
        self.lista_mesas = QListWidget()
        self.lista_mesas.setObjectName("lista_mesas_caja")
        
        left_layout.addWidget(mesas_title)
        left_layout.addWidget(self.lista_mesas)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        cuenta_title = QLabel("Detalle de la Cuenta")
        cuenta_title.setObjectName("section_title")
        
        self.tabla_cuenta = QTableWidget()
        self.tabla_cuenta.setObjectName("tabla_cuenta_caja")
        self.tabla_cuenta.setColumnCount(4)
        self.tabla_cuenta.setHorizontalHeaderLabels(["Cantidad", "Producto", "Precio Unit.", "Subtotal"])
        self.tabla_cuenta.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.total_label = QLabel("Total: C$ 0.00")
        self.total_label.setObjectName("total_label")
        
        self.cobrar_button = QPushButton("Cobrar y Cerrar Mesa")
        self.cobrar_button.setObjectName("orange_button")
        
        right_layout.addWidget(cuenta_title)
        right_layout.addWidget(self.tabla_cuenta)
        right_layout.addWidget(self.total_label)
        right_layout.addWidget(self.cobrar_button)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.lista_mesas.itemClicked.connect(self.mostrar_cuenta_de_mesa)
        self.cobrar_button.clicked.connect(self.cobrar_cuenta)
        
        self.load_active_orders()
        self.app_controller.ordenes_actualizadas.connect(self.load_active_orders)

    def load_active_orders(self):
        mesa_previa = self.mesa_actual
        
        self.ordenes_activas = {} 
        self.lista_mesas.clear() 
        
        try:
            self.ordenes_activas = self.app_controller.data_manager.get_active_orders_caja()
            
            sorted_keys = sorted(self.ordenes_activas.keys())

            for mesa_key in sorted_keys:
                orden = self.ordenes_activas[mesa_key]

                if not orden['items']:
                    continue

                mesa_display_text = ""
                
                base_key = mesa_key
                es_subcuenta = False
                numero_subcuenta = 0
                
                if "-" in mesa_key:
                    try:
                        partes = mesa_key.rsplit('-', 1)
                        if len(partes) == 2 and partes[1].isdigit():
                            base_key = partes[0]
                            numero_subcuenta = int(partes[1]) 
                            es_subcuenta = True
                    except:
                        pass 

                if "+" in base_key:
                    texto_mesa = f"Grupo {base_key}"
                else:
                    texto_mesa = f"Mesa {base_key}"

                if es_subcuenta and numero_subcuenta > 0:
                    mesa_display_text = f"{texto_mesa}: Sub Cuenta {numero_subcuenta}"
                else:
                    mesa_display_text = texto_mesa
                
                item = QListWidgetItem(mesa_display_text)
                item.setData(100, mesa_key) 
                self.lista_mesas.addItem(item)
                
            if mesa_previa:
                if mesa_previa in self.ordenes_activas and self.ordenes_activas[mesa_previa]['items']:
                    for i in range(self.lista_mesas.count()):
                        item_widget = self.lista_mesas.item(i)
                        if item_widget.data(100) == mesa_previa:
                            self.lista_mesas.setCurrentItem(item_widget)
                            self._llenar_tabla_detalle(self.ordenes_activas[mesa_previa])
                            break
                else:
                    self._limpiar_tabla()
                    self.mesa_actual = None

        except Exception as e:
            print(f"Error cargando órdenes: {e}")
            self.ordenes_activas = {}

    def mostrar_cuenta_de_mesa(self, item):
        if not item:
            self._limpiar_tabla()
            self.mesa_actual = None
            return

        mesa_key = item.data(100) 
        self.mesa_actual = mesa_key 
        
        if mesa_key and mesa_key in self.ordenes_activas:
            self._llenar_tabla_detalle(self.ordenes_activas[mesa_key])
        else:
            self._limpiar_tabla()
            
    def _llenar_tabla_detalle(self, orden):
        """Helper para llenar la tabla derecha y calcular totales."""
        self.tabla_cuenta.setRowCount(0) 
        self.tabla_cuenta.setRowCount(len(orden['items']))
        
        total = 0.0
        for row, platillo in enumerate(orden['items']):
            cantidad = platillo['cantidad']
            nombre = platillo['nombre']
            precio = platillo['precio_unitario']
            subtotal = cantidad * precio
            total += subtotal
            
            qty_item = QTableWidgetItem(str(cantidad))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.tabla_cuenta.setItem(row, 0, qty_item)
            self.tabla_cuenta.setItem(row, 1, QTableWidgetItem(nombre))
            self.tabla_cuenta.setItem(row, 2, QTableWidgetItem(f"C$ {precio:.2f}"))
            self.tabla_cuenta.setItem(row, 3, QTableWidgetItem(f"C$ {subtotal:.2f}"))
            
        self.total_label.setText(f"Total: C$ {total:.2f}")

    def cobrar_cuenta(self):
        item_seleccionado = self.lista_mesas.currentItem()
        if not item_seleccionado: 
            QMessageBox.warning(self, "Acción no válida", "Por favor, seleccione una mesa para cobrar.")
            return
        
        texto_item = item_seleccionado.text()
        mesa_key = item_seleccionado.data(100)
        
        if mesa_key:
            exito = self.app_controller.cobrar_cuenta(mesa_key)
            
            if exito:
                QMessageBox.information(self, "Cobro Exitoso", f"La {texto_item} ha sido cobrada y cerrada.")
                self._limpiar_tabla()
                self.mesa_actual = None
            else:
                QMessageBox.critical(self, "Error", "No se pudo cerrar la cuenta en la base de datos.")

    def _limpiar_tabla(self):
        self.tabla_cuenta.setRowCount(0)
        self.total_label.setText("Total: C$ 0.00")

    def _extraer_mesa_key(self, texto):
        if texto.startswith("Mesas "):
            return texto.split(" ")[1]
        elif texto.startswith("Mesa "):
            return texto.split(" ")[1]
        return ""