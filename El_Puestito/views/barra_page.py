from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, 
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSlot
from widgets.order_ticket import OrderTicket

class BarraPage(QWidget):
    def __init__(self, controller,main_window):
        super().__init__()
        self.controller = controller
        self.main_window = main_window
        self.tickets_en_pantalla = {}
        self.setup_ui()
        self.controller.ordenes_actualizadas.connect(self.load_active_orders)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Comandas de Barra")
        header.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px; color: #ffffff;")
        layout.addWidget(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scroll_area_barra")

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
        datos_ordenes = self.controller.data_manager.get_active_barra_orders()
        
        ordenes_actuales = { str(orden['numero_mesa']): orden for orden in datos_ordenes }
        
        ids_bd = set(ordenes_actuales.keys())
        ids_pantalla = set(self.tickets_en_pantalla.keys())

        a_borrar = ids_pantalla - ids_bd
        for mesa_key in a_borrar:
            self._remover_ticket(mesa_key)

        a_agregar = ids_bd - ids_pantalla
        for mesa_key in a_agregar:
            datos = ordenes_actuales[mesa_key]
            self._agregar_ticket(mesa_key, datos)

    def _agregar_ticket(self, key, datos):
        ticket_widget = OrderTicket(datos)
        ticket_widget.btn_listo.clicked.connect(lambda: self._marcar_listo(key))
        
        count = len(self.tickets_en_pantalla)
        row = count // 4
        col = count % 4
        
        self.grid_layout.addWidget(ticket_widget, row, col)
        self.tickets_en_pantalla[key] = ticket_widget

    def _remover_ticket(self, key):
        if key in self.tickets_en_pantalla:
            widget = self.tickets_en_pantalla.pop(key)
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()
            self._reorganizar_grid()

    def _reorganizar_grid(self):
        """Recalcula las posiciones de todos los tickets restantes."""
        widgets_ordenados = list(self.tickets_en_pantalla.values())
        
        for i, widget in enumerate(widgets_ordenados):
            row = i // 4
            col = i % 4
            self.grid_layout.addWidget(widget, row, col)

    def _marcar_listo(self, mesa_key):
        self.controller.data_manager.mark_barra_order_ready(mesa_key)
        self.load_active_orders()
        if self.main_window and hasattr(self.main_window, 'server_worker'):
            self.main_window.server_worker.forzar_actualizacion_kds('barra')