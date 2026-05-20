import os
import json
import datetime
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from flask import Flask
from flask_socketio import SocketIO
from logger_setup import setup_logger
from server.server_routes import api_bp
from path_manager import get_persistent_path, get_base_dir

logger = setup_logger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(get_base_dir(), 'server', 'templates')
STATIC_DIR = os.path.join(get_base_dir(), 'server', 'static')

class ServerWorker(QObject):
    asistencia_recibida = pyqtSignal(dict)
    nueva_orden_recibida = pyqtSignal(dict)
    kds_estado_cambiado = pyqtSignal(str)
    ordenes_modificadas = pyqtSignal()
    server_error = pyqtSignal(str)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.config = self._load_config()
        self.API_KEY = self.config.get('api_key', os.environ.get('PUESTITO_API_KEY', os.urandom(24).hex()))
        
        self.PINS_WEB_MAP = {}
        self.cargar_pines_kds()

        self.last_enrolled_id = None
        self.enroll_mode_active = False
        self.clear_mode_active = False
        self.enroll_status = {"step": 0, "message": "Esperando inicio..."}

        self.app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
        self.app.secret_key = self.config.get('secret_key', os.environ.get('PUESTITO_SECRET_KEY', os.urandom(24).hex()))
        self.app.worker = self
        self.app.register_blueprint(api_bp)

        @self.app.teardown_appcontext
        def close_db_connection(exception=None):
            self.data_manager.close_conn_for_thread()

        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*", 
            async_mode='threading',
            manage_session=False
        )

    def _load_config(self):
        try:
            path = get_persistent_path("config.json")
            if not os.path.exists(path):
                return {}
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando config: {e}")
            return {}

    def cargar_pines_kds(self):
        self.config = self._load_config()
        self.PINS_WEB_MAP.clear()
        
        seguridad = self.config.get('seguridad', {})
        pines = seguridad.get('pines_acceso', {})
        
        if isinstance(pines, dict):
            for rol, pin in pines.items():
                rol_lower = str(rol).lower()
                if 'cocin' in rol_lower: 
                    self.PINS_WEB_MAP[str(pin).strip()] = 'cocina'
                elif 'barra' in rol_lower or 'michel' in rol_lower:
                    self.PINS_WEB_MAP[str(pin).strip()] = 'barra'
                    
        logger.info(f"PINs cargados: {self.PINS_WEB_MAP}")

    def forzar_actualizacion_kds(self, destino):
        try:
            self.socketio.emit('kds_update', {'destino': destino})
            self.socketio.emit('mesas_actualizadas', self.data_manager.get_active_orders_caja())
        except Exception as e:
            logger.error(f"Error emitiendo socket: {e}")

    def _validate_order_items(self, orden):
        try:
            available_ids = self.data_manager.get_available_menu_items()
            items_en_orden = orden.get("items", [])
            
            cantidades_requeridas = {}
            for item_in_order in items_en_orden:
                item_id = item_in_order.get("item_id")
                cantidad = item_in_order.get("cantidad", 1)
                item_nombre = item_in_order.get("nombre", "Desconocido")
                
                if item_id not in available_ids:
                    return False, f"El platillo '{item_nombre}' ya no está disponible."
                    
                if item_id in cantidades_requeridas:
                    cantidades_requeridas[item_id]["cantidad"] += cantidad
                else:
                    cantidades_requeridas[item_id] = {"cantidad": cantidad, "nombre": item_nombre}
                    
            for item_id, data in cantidades_requeridas.items():
                stock_info = self.data_manager.fetchone("SELECT cantidad, es_automatico FROM inventario WHERE id_menu_vinculado = ?", (item_id,))
                if stock_info and stock_info['es_automatico'] == 1:
                    if data["cantidad"] > stock_info['cantidad']:
                        return False, f"Stock insuficiente para '{data['nombre']}'. Disponible: {stock_info['cantidad']}."
                        
            return True, ""
        except Exception:
            return False, "Error interno al validar el menú."
        
    def _registrar_evento(self, emp_id, tipo):
        ts = datetime.datetime.now().isoformat(timespec='seconds')
        self.data_manager.add_attendance_event(emp_id, tipo, ts)
        self.asistencia_recibida.emit({
            "employee_id": emp_id, "event_type": tipo, "timestamp": ts
        })

    def stop_server(self):
        try:
            self.socketio.stop()
        except Exception as e:
            logger.error(f"Error deteniendo SocketIO: {e}")

    def start_server(self):
        try:
            self.socketio.run(
                self.app, 
                host='0.0.0.0', 
                port=5000, 
                log_output=True,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logger.critical(f"Fallo en servidor: {e}")
            self.server_error.emit(str(e))