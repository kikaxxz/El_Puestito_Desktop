from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, 
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSlot
from widgets.order_ticket import OrderTicket
from logger_setup import setup_logger

logger = setup_logger()

class CocinaPage(QWidget):
    def __init__(self, controller, main_window):
        super().__init__()
        self.controller = controller
        self.main_window = main_window
        self.tickets_en_pantalla = {}
        self.columnas_grid = 4
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
        try:
            from src.database.repositories.orders import order_repo
            datos_ordenes = order_repo.get_active_cocina_orders()
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
                self.tickets_en_pantalla[mesa_key].update_data(ordenes_actuales[mesa_key])

            self._reorganizar_grid()
        except Exception as e:
            logger.error(f"Error cargando comandas activas de cocina: {e}")

    def _crear_widget_memoria(self, key, datos):
        try:
            ticket_widget = OrderTicket(datos) 
            ticket_widget.btn_listo.clicked.connect(lambda: self._marcar_listo(key))
            ticket_widget.item_marcado_listo.connect(lambda id_detalle, k=key: self._marcar_item_individual(id_detalle, k))
            self.tickets_en_pantalla[key] = ticket_widget
        except Exception as e:
            logger.error(f"Error instanciando widget de orden {key}: {e}")

    def _marcar_item_individual(self, id_detalle, mesa_key):
        try:
            self.controller.procesar_item_individual_listo(id_detalle, mesa_key, "cocina")
        except Exception as e:
            logger.error(f"Error al marcar como listo el item individual {id_detalle} de la comanda {mesa_key}: {e}")

    def _eliminar_widget_memoria(self, key):
        if key in self.tickets_en_pantalla:
            widget = self.tickets_en_pantalla.pop(key)
            widget.setParent(None)
            widget.deleteLater() 

    def _reorganizar_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None) 

        keys_ordenadas = sorted(self.tickets_en_pantalla.keys())
        
        for i, key in enumerate(keys_ordenadas):
            widget = self.tickets_en_pantalla[key]
            
            if widget:
                row = i // self.columnas_grid
                col = i % self.columnas_grid
                self.grid_layout.addWidget(widget, row, col)

    def _marcar_listo(self, mesa_key):
        try:
            from src.services.order_service import order_service
            order_service.mark_order_ready(mesa_key, 'cocina')
            self.load_active_orders()
            self.controller.notificar_cambios_mesas()
        except Exception as e:
            logger.error(f"Error al marcar como lista la comanda {mesa_key}: {e}")
    
    def _marcar_listo(self, mesa_key):
        try:
            from src.services.order_service import order_service
            order_service.mark_order_ready(mesa_key, 'cocina')
            self.load_active_orders()
            self.controller.notificar_cambios_mesas()
            self.controller.notificar_alerta_kds(mesa_key, "cocina")
        except Exception as e:
            logger.error(f"Error al marcar como lista la comanda {mesa_key}: {e}")