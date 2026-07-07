import os
import json
import datetime
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from flask import Flask, session
from flask_socketio import SocketIO, join_room, disconnect
from logger_setup import setup_logger
from server.routes import api_bp
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

    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.API_KEY = self.config.get('api_key', 'puestito_seguro_2025')
        
        self.PINS_WEB_MAP = {}
        self.cargar_pines_kds()

        self.last_enrolled_id = None
        self.enroll_mode_active = False
        self.clear_mode_active = False
        self.enroll_status = {"step": 0, "message": "Esperando inicio..."}

        self.app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
        self.app.secret_key = self._get_or_create_secret_key()
        self.app.worker = self
        self.app.register_blueprint(api_bp)

        @self.app.teardown_appcontext
        def close_db_connection(exception=None):
            from src.database.connection import db_manager
            db_manager.close_conn_for_thread()

        self.socketio = SocketIO(
            self.app, 
            async_mode='threading'
        )

        @self.socketio.on('connect')
        def on_connect():
            from flask import request
            api_key = request.args.get('api_key')
            
            if api_key and api_key == self.API_KEY:
                logger.info("Cliente movil conectado via API KEY")
                return True
                
            destino = session.get('kds_access')
            if not destino:
                logger.warning("Conexion Socket.IO rechazada: No hay sesion KDS activa ni API_KEY")
                disconnect()
                return False
            
            join_room(destino)
            logger.info(f"Cliente conectado y unido a sala: {destino}")

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

    def _get_or_create_secret_key(self):
        secret_path = get_persistent_path("secret.key")
        if os.path.exists(secret_path):
            with open(secret_path, 'r') as f:
                return f.read().strip()
        else:
            new_key = os.urandom(24).hex()
            try:
                with open(secret_path, 'w') as f:
                    f.write(new_key)
            except Exception as e:
                logger.error(f"Error guardando secret.key: {e}")
            return new_key

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
            from src.services.order_service import order_service
            self.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
        except Exception as e:
            logger.error(f"Error emitiendo socket: {e}")

    def _validate_order_items(self, orden):
        try:
            from src.database.repositories.menu import menu_repo
            from src.database.repositories.inventory import inventory_repo
            available_ids = menu_repo.get_available_menu_items()
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
                stock_info = inventory_repo.get_inventario_item_by_menu(item_id)
                if stock_info and stock_info['es_automatico'] == 1:
                    if data["cantidad"] > stock_info['cantidad']:
                        return False, f"Stock insuficiente para '{data['nombre']}'. Disponible: {stock_info['cantidad']}."
                        
            return True, ""
        except Exception:
            return False, "Error interno al validar el menú."
            
    def on_internal_emit(self, event_name, payload_data):
        logger.info(f"Retransmitiendo evento interno: {event_name}")
        
        if event_name == 'config_update':
            self.cargar_pines_kds()
            self.socketio.emit('config_update', payload_data)

        elif event_name in ['mesas_actualizadas', 'mesas_update', 'order_updated']:
            def emit_update():
                self.socketio.sleep(0.1)
                from src.services.order_service import order_service
                table_state_payload = order_service.get_active_orders_caja()
                self.socketio.emit('mesas_actualizadas', table_state_payload)
            self.socketio.start_background_task(emit_update)
            
        elif event_name == 'menu_actualizado':
            self.socketio.emit('menu_actualizado', {'mensaje': 'Menu cambiado'})
            
        elif event_name == 'api/biometric/start-clear':
            self.clear_mode_active = True
            
        else:
            if payload_data:
                self.socketio.emit(event_name, payload_data)
            else:
                self.socketio.emit(event_name)
        
    def _registrar_evento(self, emp_id, tipo):
        ts = datetime.datetime.now().isoformat(timespec='seconds')
        from src.services.attendance_service import attendance_service
        attendance_service.add_attendance_event(emp_id, tipo, ts)
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