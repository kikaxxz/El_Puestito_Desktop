from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, 
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSlot
from widgets.order_ticket import OrderTicket

class CocinaPage(QWidget):
    def __init__(self, controller, main_window):
        super().__init__()
        self.controller = controller
        self.main_window = main_window
        self.tickets_en_pantalla = {} 
        self.setup_ui()
        
        self.controller.ordenes_actualizadas.connect(self.load_active_orders)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Comandas de Cocina")
        header.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px; color: #ffffff;")
        layout.addWidget(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scroll_area_cocina")
        
        self.container_widget = QWidget()
        self.container_widget.setObjectName("tickets_container")
        
        self.grid_layout = QGridLayout(self.container_widget)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll_area.setWidget(self.container_widget)
        layout.addWidget(scroll_area)

        self.load_active_orders()

    @pyqtSlot()
    def load_active_orders(self):
        datos_ordenes = self.controller.data_manager.get_active_cocina_orders()
        ordenes_actuales = { str(orden['numero_mesa']): orden for orden in datos_ordenes }
        
        ids_bd = set(ordenes_actuales.keys())
        ids_pantalla = set(self.tickets_en_pantalla.keys())

        a_borrar = ids_pantalla - ids_bd
        for mesa_key in a_borrar:
            self._eliminar_widget_memoria(mesa_key)

        a_agregar = ids_bd - ids_pantalla
        for mesa_key in a_agregar:
            self._crear_widget_memoria(mesa_key, ordenes_actuales[mesa_key])
            
        a_actualizar = ids_bd.intersection(ids_pantalla)
        for mesa_key in a_actualizar:
            self._eliminar_widget_memoria(mesa_key)
            self._crear_widget_memoria(mesa_key, ordenes_actuales[mesa_key])

        self._reorganizar_grid()

    def _crear_widget_memoria(self, key, datos):
        """Crea el widget y lo guarda en el diccionario, pero NO lo agrega al grid todavía."""
        ticket_widget = OrderTicket(datos) 
        ticket_widget.btn_listo.clicked.connect(lambda: self._marcar_listo(key))
        self.tickets_en_pantalla[key] = ticket_widget

    def _eliminar_widget_memoria(self, key):
        """Elimina el widget del diccionario y lo destruye."""
        if key in self.tickets_en_pantalla:
            widget = self.tickets_en_pantalla.pop(key)
            widget.setParent(None)
            widget.deleteLater() 

    def _reorganizar_grid(self):
        """Limpia el layout visualmente y reubica todos los widgets en orden."""

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None) 

        keys_ordenadas = sorted(self.tickets_en_pantalla.keys())
        
        for i, key in enumerate(keys_ordenadas):
            widget = self.tickets_en_pantalla[key]
            
            if widget:
                row = i // 4
                col = i % 4
                self.grid_layout.addWidget(widget, row, col)

    def _marcar_listo(self, mesa_key):
        self.controller.data_manager.mark_cocina_order_ready(mesa_key)
        
        self.load_active_orders()
        
        self.controller.notificar_cambios_mesas()