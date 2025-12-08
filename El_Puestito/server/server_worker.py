import os
import json
import datetime
import requests
import time
import threading 
from functools import wraps
import eventlet 
from PyQt6.QtCore import QObject, pyqtSignal
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_socketio import SocketIO

from logger_setup import setup_logger
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

        self.app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        worker_self = self

        def require_auth(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if request.method == 'OPTIONS':
                    return f(*args, **kwargs)
                
                token = request.headers.get('X-API-KEY')
                if token != worker_self.API_KEY:
                    logger.warning(f"Intento de acceso no autorizado desde {request.remote_addr}")
                    return jsonify({"error": "Unauthorized", "message": "Falta API Key válida"}), 401
                
                return f(*args, **kwargs)
            return decorated


        @self.app.route('/')
        def index():
            return render_template('login.html')

        @self.app.route('/kds/<destino>')
        def kds_view(destino):
            if destino not in ['cocina', 'barra']:
                return "Destino no válido", 404
            return render_template('kds_view.html', destino=destino, api_key=worker_self.API_KEY)

        @self.app.route('/api/validar-pin', methods=['POST'])
        def validar_pin():
            data = request.json
            pin = data.get('pin')
            destino = worker_self.PINS_WEB_MAP.get(str(pin))
            
            if destino:
                logger.info(f"Acceso KDS web autorizado para: {destino}")
                return jsonify({"status": "success", "redirect": f"/kds/{destino}"})
            else:
                logger.warning("Intento de PIN incorrecto en KDS web")
                return jsonify({"status": "error", "message": "PIN Incorrecto"}), 401

        @self.app.route('/api/kds-orders/<destino>', methods=['GET'])
        def get_kds_orders(destino):
            if destino == 'cocina':
                ordenes = worker_self.data_manager.get_active_cocina_orders()
            elif destino == 'barra':
                ordenes = worker_self.data_manager.get_active_barra_orders()
            else:
                return jsonify([]), 400
            return jsonify(ordenes)

        @self.app.route('/api/kds-complete', methods=['POST'])
        @require_auth
        def complete_kds_order():
            data = request.json
            mesa_key = data.get('mesa_key')
            destino = data.get('destino')
            
            if destino == 'cocina':
                worker_self.data_manager.mark_cocina_order_ready(mesa_key)
            elif destino == 'barra':
                worker_self.data_manager.mark_barra_order_ready(mesa_key)
            
            logger.info(f"Orden Mesa {mesa_key} marcada lista en {destino} (vía Web)")
            
            worker_self.socketio.emit('kds_update', {'destino': destino})
            worker_self.kds_estado_cambiado.emit(destino)
            worker_self.socketio.emit('mesas_actualizadas', worker_self._get_table_state())
            return jsonify({"status": "success"}), 200

        @self.app.route('/reportes-web')
        def view_reportes():
            return render_template('reportes_dashboard.html')

        @self.app.route('/api/chart-data', methods=['GET'])
        def get_chart_data():
            try:
                start_arg = request.args.get('start')
                end_arg = request.args.get('end')
                
                tendencia = worker_self.data_manager.get_sales_history_range(
                    start_date=start_arg if start_arg else None, 
                    end_date=end_arg if end_arg else None
                )
                
                hoy = datetime.date.today().isoformat()
                
                if start_arg and end_arg:
                    top_items = worker_self.data_manager.get_top_products_range(start_arg, end_arg)
                else:
                    top_items = worker_self.data_manager.get_top_products_range(hoy, hoy)

                top_platillos = {
                    "nombres": [item['nombre'] for item in top_items],
                    "cantidades": [item['cantidad_total'] for item in top_items]
                }
                
                total_hoy, _ = worker_self.data_manager.get_sales_report(hoy)
                
                return jsonify({
                    "tendencia": tendencia,
                    "top_productos": top_platillos,
                    "resumen_hoy": {"total": total_hoy} 
                })

            except Exception as e:
                logger.error(f"Error generando datos para gráficas: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown():
            return jsonify({"status": "shutdown_ignored_in_threading_mode"})

        @self.app.route('/registrar', methods=['POST'])
        @require_auth
        def registrar_asistencia_movil():
            data = request.json

            if not data or 'employee_id' not in data or 'deviceId' not in data:
                return jsonify({"error": "Datos incompletos"}), 400

            employee_id = data['employee_id']
            device_id = data['deviceId']
            
            empleado = self.data_manager.get_employee_by_id(employee_id)
            if not empleado:
                return jsonify({"error": "not_found"}), 404
            
            if not empleado.get("deviceId"):
                self.data_manager.link_device_to_employee(employee_id, device_id)
                self._registrar_evento(employee_id, "entrada")
                logger.info(f"Dispositivo vinculado para empleado {employee_id}")
                return jsonify({"status": "success", "message": "Dispositivo vinculado y entrada marcada"}), 201
            
            elif empleado.get("deviceId") != device_id:
                logger.warning(f"Intento de asistencia fallido: DeviceID incorrecto para {employee_id}")
                return jsonify({"error": "device_mismatch"}), 403
            
            last_event = self.data_manager.get_last_attendance_event(employee_id)
            tipo = "salida" if last_event and last_event['tipo'] == 'entrada' else "entrada"
            self._registrar_evento(employee_id, tipo)
            
            return jsonify({"status": "success", "message": f"{tipo.capitalize()} registrada"}), 200
        
        @self.app.route('/configuracion', methods=['GET'])
        @require_auth
        def get_configuracion():
            try:
                config_path = os.path.join(BASE_DIR, "assets", "config.json")
                with open(config_path, 'r') as f:
                    return jsonify(json.load(f))
            except Exception as e:
                logger.error(f"Error sirviendo configuración: {e}")
                return jsonify({"error": "Error cargando config"}), 500
            
        @self.app.route('/images/<path:filename>')
        def serve_image(filename):
            image_directory = os.path.join(BASE_DIR, "assets")
            try:
                return send_from_directory(image_directory, filename)
            except FileNotFoundError:
                return jsonify({"error": "Image not found"}), 404
            
        @self.app.route('/menu', methods=['GET'])
        @require_auth
        def get_menu():
            try:
                menu_data = worker_self.data_manager.get_menu_with_categories()
                
                menu_filtrado = {"categorias": []}
                
                for categoria_original in menu_data.get("categorias", []):
                    items_disponibles = [
                        item for item in categoria_original.get("items", [])
                        if item.get("disponible", True) 
                    ]
                    
                    if items_disponibles:
                        nueva_categoria = categoria_original.copy()
                        items_app_format = []
                        for item in items_disponibles:
                            item_copy = item.copy()
                            item_copy['id'] = item_copy.pop('id_item', item_copy.get('id'))
                            items_app_format.append(item_copy)
                        
                        nueva_categoria["items"] = items_app_format
                        menu_filtrado["categorias"].append(nueva_categoria)
                
                return jsonify(menu_filtrado)
            except Exception as e:
                logger.error(f"Error sirviendo menú: {e}")
                return jsonify({"error": "No se pudo cargar el menú"}), 500
            
        @self.app.route('/nueva-orden', methods=['POST'])
        @require_auth
        def recibir_orden():
            orden = request.json
            
            is_valid, error_msg = worker_self._validate_order_items(orden)
            if not is_valid:
                return jsonify({"error": "Item Agotado", "mensaje": error_msg}), 400
            
            order_id = orden.get("order_id")
            if worker_self.data_manager.check_duplicate_order_id(order_id):
                return jsonify({"status": "ok_duplicate"}), 200
            
            logger.info(f"Nueva orden recibida vía API: {order_id}")
            worker_self.nueva_orden_recibida.emit(orden) 
            worker_self.socketio.emit('kds_update', {'destino': 'all'})

            return jsonify({"status": "ok_new"}), 200
        
        @self.app.route('/api/split-order', methods=['POST'])
        @require_auth
        def split_order_endpoint():
            data = request.json
            mesa_key = data.get('mesa_key')
            items = data.get('items') 
            
            if not mesa_key or not items:
                return jsonify({"error": "Datos incompletos"}), 400
                
            success = worker_self.data_manager.split_order(mesa_key, items)
            
            if success:
                logger.info(f"Cuenta separada exitosamente en Mesa {mesa_key}")
                worker_self.socketio.emit('mesas_actualizadas', worker_self._get_table_state())
                worker_self.ordenes_modificadas.emit() 
                return jsonify({"status": "success"}), 200
            else:
                logger.error(f"Fallo al separar cuenta en Mesa {mesa_key}")
                return jsonify({"error": "Error al dividir cuenta"}), 500

        @self.app.route('/employees', methods=['GET'])
        @require_auth
        def get_employees():
            employees_full = worker_self.data_manager.get_employees() 
            if employees_full is None:
                return jsonify({"error": "No se pudo cargar la lista de empleados"}), 500
            
            employee_list = [
                {"id": emp.get("id_empleado"), "nombre": emp.get("nombre")}
                for emp in employees_full
                if emp.get("id_empleado") and emp.get("nombre") 
            ]
            return jsonify(employee_list)
        
        @self.app.route('/estado-mesas', methods=['GET'])
        @require_auth
        def get_estado_mesas():
            try:
                caja_data = worker_self.data_manager.get_active_orders_caja()
                return jsonify(caja_data)
            except Exception as e:
                logger.error(f"Error obteniendo estado mesas: {e}")
                return jsonify({"error": "No se pudo cargar el estado de las mesas"}), 500
            
        @self.app.route('/trigger_update', methods=['POST'])
        @require_auth
        def trigger_update():
            data = request.json
            event_name = data.get('event')
            payload_data = data.get('data') 
            
            logger.info(f"Retransmitiendo evento: {event_name}")
            
            if event_name == 'mesas_actualizadas':
                time.sleep(0.1) 
                table_state_payload = worker_self._get_table_state()
                worker_self.socketio.emit('mesas_actualizadas', table_state_payload)
                
            elif event_name == 'menu_actualizado':
                worker_self.socketio.emit('menu_actualizado', {'mensaje': 'Menú cambiado'})
            
            else:
                if payload_data:
                    worker_self.socketio.emit(event_name, payload_data)
                else:
                    worker_self.socketio.emit(event_name)

            return jsonify({"status": "emitted"}), 200
        
        @self.app.route('/api/cancel-order', methods=['POST'])
        @require_auth
        def cancel_order_endpoint():
            data = request.json
            mesa_key = data.get('mesa_key')
            
            if not mesa_key: return jsonify({"error": "Falta mesa_key"}), 400
            
            success = worker_self.data_manager.cancel_order_by_key(mesa_key)
            
            if success:
                logger.info(f"Orden cancelada manualmente: Mesa {mesa_key}")
                worker_self.socketio.emit('mesas_actualizadas', worker_self._get_table_state())
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"error": "No se pudo cancelar (¿Tiene productos?)"}), 400

        @self.app.route('/api/remove-items', methods=['POST'])
        @require_auth
        def remove_items_endpoint():
            data = request.json
            mesa_key = data.get('mesa_key')
            items = data.get('items')
            
            if not mesa_key or not items:
                return jsonify({"error": "Datos incompletos"}), 400
                
            success = worker_self.data_manager.remove_items_from_order(mesa_key, items)
            
            if success:
                logger.info(f"Items eliminados de Mesa {mesa_key}")
                worker_self.socketio.emit('mesas_actualizadas', worker_self._get_table_state())
                worker_self.socketio.emit('kds_update', {'destino': 'cocina'})
                worker_self.socketio.emit('kds_update', {'destino': 'barra'})
                worker_self.ordenes_modificadas.emit() 
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"error": "No se pudieron eliminar"}), 400
    
    def _load_config(self):
        """Carga la configuración desde config.json de forma segura."""
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
        self.socketio.emit('mesas_actualizadas', self._get_table_state())
            
    def _get_table_state(self):
        try:
            caja_data = self.data_manager.get_active_orders_caja()
            return caja_data 
        except Exception as e:
            logger.error(f"Error obteniendo estado de mesas: {e}")
            return {}

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
            logger.info("Iniciando servidor Flask/SocketIO en puerto 5000...")
            self.socketio.run(self.app, 
                            host='0.0.0.0', 
                            port=5000, 
                            allow_unsafe_werkzeug=True, 
                            log_output=False) 
        except Exception as e:
            logger.critical(f"Fallo fatal en el servidor: {e}", exc_info=True)