from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt

from widgets.order_ticket import OrderTicketWidget

class CocinaPage(QWidget):
    
    def load_active_orders(self):
        """Carga las órdenes de cocina activas desde la BD y las muestra."""
        
        while self.ticket_container_layout.count():
            item = self.ticket_container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        self.active_orders_data = [] 
        try:
            self.active_orders_data = self.app_controller.data_manager.get_active_cocina_orders()
            print(f"🍳 Órdenes de cocina cargadas desde la BD")
            for orden_data in self.active_orders_data:
                self._display_order_ticket(orden_data)
        except Exception as e:
            print(f"❌ Error al cargar órdenes de cocina desde la BD: {e}")
            self.active_orders_data = []

    def _display_order_ticket(self, orden_data):
        """Función auxiliar para crear y mostrar un ticket (evita duplicar código)."""
        nuevo_ticket = OrderTicketWidget(orden_data)
        nuevo_ticket.orden_lista.connect(self.remover_orden)
        self.ticket_container_layout.addWidget(nuevo_ticket)

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        
        main_layout = QVBoxLayout(self)
        
        title = QLabel("Órdenes Entrantes")
        title.setObjectName("section_title")
        main_layout.addWidget(title)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) 
        main_layout.addWidget(scroll_area)
        
        container_widget = QWidget()
        self.ticket_container_layout = QVBoxLayout(container_widget)
        self.ticket_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(container_widget)
        
        self.load_active_orders()
        self.app_controller.ordenes_actualizadas.connect(self.load_active_orders)

    def remover_orden(self, ticket_widget):
        print("✅ Orden de cocina marcada como lista. Actualizando BD...")
        
        mesa_label_text = ticket_widget.findChild(QLabel, "ticket_title").text() 
        mesa_num_str = mesa_label_text.split(": ")[1]
        
        try:
            self.app_controller.data_manager.mark_cocina_order_ready(mesa_num_str)
            
            self.load_active_orders()
        except Exception as e:
            print(f"❌ Error al marcar orden de cocina como lista: {e}")
            
            self.ticket_container_layout.removeWidget(ticket_widget)
            ticket_widget.deleteLater()