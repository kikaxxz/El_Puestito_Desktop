import os
import json
import datetime
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from flask import Flask
from flask_socketio import SocketIO
from logger_setup import setup_logger
from server.server_routes import api_bp

logger = setup_logger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

class ServerWorker(QObject):
    class ServerShutdownException(Exception):
        pass

    asistencia_recibida = pyqtSignal(dict)
    nueva_orden_recibida = pyqtSignal(dict)
    kds_estado_cambiado = pyqtSignal(str)
    ordenes_modificadas = pyqtSignal()

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager 
        self.config = self._load_config()
        self.API_KEY = self.config.get('api_key', 'puestito_seguro_2025')
        
        seguridad = self.config.get('seguridad', {})
        self.PINS_ACCESO = seguridad.get('pines', {})
        
        self.PINS_WEB_MAP = {}
        for rol, pin in self.PINS_ACCESO.items():
            if rol.lower() in ['cocinero', 'cocina']:
                self.PINS_WEB_MAP[str(pin)] = 'cocina'
            elif rol.lower() in ['barra', 'michelero']:
                self.PINS_WEB_MAP[str(pin)] = 'barra'

        self.last_enrolled_id = None
        self.enroll_mode_active = False
        self.clear_mode_active = False
        self.enroll_status = {"step": 0, "message": "Esperando inicio..."}

        self.app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
        self.app.worker = self 
        self.app.register_blueprint(api_bp)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')

    def _load_config(self):
        try:
            path = os.path.join(BASE_DIR, "assets", "config.json")
            if not os.path.exists(path):
                logger.warning("config.json no encontrado, usando valores por defecto.")
                return {}
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error crítico cargando config.json: {e}")
            return {}

    def forzar_actualizacion_kds(self, destino):
        logger.info(f"Enviando actualización forzada a KDS Web: {destino}")
        self.socketio.emit('kds_update', {'destino': destino})
        self.socketio.emit('mesas_actualizadas', self.data_manager.get_active_orders_caja())
            
    def _validate_order_items(self, orden):
        try:
            available_ids = self.data_manager.get_available_menu_items()
            items_en_orden = orden.get("items", [])
            for item_in_order in items_en_orden:
                item_id = item_in_order.get("item_id") 
                if item_id not in available_ids:
                    item_nombre = item_in_order.get("nombre", "Desconocido")
                    return False, f"El platillo '{item_nombre}' ya no está disponible."
            return True, ""
        except Exception as e:
            logger.error(f"Error validando orden: {e}")
            return False, "Error interno al validar el menú."
        
    def _registrar_evento(self, emp_id, tipo):
        ts = datetime.datetime.now().isoformat(timespec='seconds')
        self.data_manager.add_attendance_event(emp_id, tipo, ts)
        logger.info(f"Asistencia registrada: {emp_id} - {tipo}")
        self.asistencia_recibida.emit({
            "employee_id": emp_id, "event_type": tipo, "timestamp": ts
        })

    def stop_server(self):
        pass

    def start_server(self):
        try:
            logger.info("Iniciando servidor Flask/SocketIO en puerto 5000 (Modo Threading)...")
            self.socketio.run(self.app, 
                            host='0.0.0.0', 
                            port=5000, 
                            allow_unsafe_werkzeug=True, 
                            log_output=False) 
        except Exception as e:
            logger.critical(f"Fallo fatal en el servidor: {e}", exc_info=True)