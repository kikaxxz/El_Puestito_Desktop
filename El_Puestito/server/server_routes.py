import os
import json
import datetime
import time
from functools import wraps
from flask import Blueprint, request, jsonify, send_from_directory, render_template, current_app, session, redirect, url_for
from logger_setup import setup_logger

logger = setup_logger()

api_bp = Blueprint('api', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@api_bp.route('/api/biometric/update-progress', methods=['POST'])
def update_enroll_progress():
    """El ESP32 llama aquí para avisar en qué paso va."""
    worker = current_app.worker
    data = request.json
    step = data.get('step')
    msg = data.get('message')
    
    worker.enroll_status = {"step": step, "message": msg}
    return jsonify({"status": "ok"})

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        worker = current_app.worker
        token = request.headers.get('X-API-KEY')
        
        if token != worker.API_KEY:
            logger.warning(f"Intento de acceso no autorizado desde {request.remote_addr}")
            return jsonify({"error": "Unauthorized", "message": "Falta API Key válida"}), 401
        
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/')
def index():
    return render_template('login.html')

@api_bp.route('/kds/<destino>')
def kds_view(destino):
    if destino not in ['cocina', 'barra']:
        return "Destino no válido", 404
    if session.get('kds_access') != destino:
        return redirect(url_for('api.index'))

    return render_template('kds_view.html', destino=destino, api_key=current_app.worker.API_KEY)
@api_bp.route('/reportes-web')
def view_reportes():
    return render_template('reportes_dashboard.html')

@api_bp.route('/api/validar-pin', methods=['POST'])
def validar_pin():
    worker = current_app.worker
    data = request.json
    pin = data.get('pin')
    destino = worker.PINS_WEB_MAP.get(str(pin))
    
    if destino:
        logger.info(f"Acceso KDS web autorizado para: {destino}")
        session['kds_access'] = destino 
        return jsonify({"status": "success", "redirect": f"/kds/{destino}"})
    else:
        logger.warning("Intento de PIN incorrecto en KDS web")
        return jsonify({"status": "error", "message": "PIN Incorrecto"}), 401

@api_bp.route('/api/kds-orders/<destino>', methods=['GET'])
def get_kds_orders(destino):
    worker = current_app.worker
    if destino == 'cocina':
        ordenes = worker.data_manager.get_active_cocina_orders()
    elif destino == 'barra':
        ordenes = worker.data_manager.get_active_barra_orders()
    else:
        return jsonify([]), 400
    return jsonify(ordenes)

@api_bp.route('/api/kds-complete', methods=['POST'])
@require_auth
def complete_kds_order():
    worker = current_app.worker
    data = request.json
    mesa_key = data.get('mesa_key')
    destino = data.get('destino')
    
    if destino == 'cocina':
        worker.data_manager.mark_cocina_order_ready(mesa_key)
    elif destino == 'barra':
        worker.data_manager.mark_barra_order_ready(mesa_key)
    
    logger.info(f"Orden Mesa {mesa_key} marcada lista en {destino} (vía Web)")
    
    worker.socketio.emit('kds_update', {'destino': destino})
    worker.kds_estado_cambiado.emit(destino)
    worker.socketio.emit('mesas_actualizadas', worker.data_manager.get_active_orders_caja())
    return jsonify({"status": "success"}), 200

@api_bp.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    worker = current_app.worker
    try:
        start_arg = request.args.get('start')
        end_arg = request.args.get('end')
        
        tendencia = worker.data_manager.get_sales_history_range(
            start_date=start_arg if start_arg else None, 
            end_date=end_arg if end_arg else None
        )
        
        hoy = datetime.date.today().isoformat()
        
        if start_arg and end_arg:
            top_items = worker.data_manager.get_top_products_range(start_arg, end_arg)
        else:
            top_items = worker.data_manager.get_top_products_range(hoy, hoy)

        top_platillos = {
            "nombres": [item['nombre'] for item in top_items],
            "cantidades": [item['cantidad_total'] for item in top_items]
        }
        
        total_hoy, _ = worker.data_manager.get_sales_report(hoy)
        
        return jsonify({
            "tendencia": tendencia,
            "top_productos": top_platillos,
            "resumen_hoy": {"total": total_hoy} 
        })

    except Exception as e:
        logger.error(f"Error generando datos para gráficas: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@api_bp.route('/shutdown', methods=['POST'])
def shutdown():
    return jsonify({"status": "shutdown_ignored_in_threading_mode"})

@api_bp.route('/registrar', methods=['POST'])
@require_auth
def registrar_asistencia_movil():
    worker = current_app.worker
    data = request.json

    if not data or 'employee_id' not in data or 'deviceId' not in data:
        return jsonify({"error": "Datos incompletos"}), 400

    employee_id = data['employee_id']
    device_id = data['deviceId']
    
    empleado = worker.data_manager.get_employee_by_id(employee_id)
    if not empleado:
        return jsonify({"error": "not_found"}), 404
    
    if not empleado.get("deviceId"):
        worker.data_manager.link_device_to_employee(employee_id, device_id)
        worker._registrar_evento(employee_id, "entrada")
        logger.info(f"Dispositivo vinculado para empleado {employee_id}")
        return jsonify({"status": "success", "message": "Dispositivo vinculado y entrada marcada"}), 201
    
    elif empleado.get("deviceId") != device_id:
        logger.warning(f"Intento de asistencia fallido: DeviceID incorrecto para {employee_id}")
        return jsonify({"error": "device_mismatch"}), 403
    
    last_event = worker.data_manager.get_last_attendance_event(employee_id)

    if last_event:
        last_ts = datetime.datetime.fromisoformat(last_event['timestamp'])
        now = datetime.datetime.now()
        diff_seconds = (now - last_ts).total_seconds()
        
        if diff_seconds < 3:
            return jsonify({"status": "ignored", "message": f"Espera {3 - int(diff_seconds)}s antes de marcar de nuevo."}), 200

    tipo = "salida" if last_event and last_event['tipo'] == 'entrada' else "entrada"
    worker._registrar_evento(employee_id, tipo)
    
    return jsonify({"status": "success", "message": f"{tipo.capitalize()} registrada"}), 200

@api_bp.route('/configuracion', methods=['GET'])
@require_auth
def get_configuracion():
    try:
        config_path = os.path.join(BASE_DIR, "assets", "config.json")
        with open(config_path, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        logger.error(f"Error sirviendo configuración: {e}")
        return jsonify({"error": "Error cargando config"}), 500

@api_bp.route('/images/<path:filename>')
def serve_image(filename):
    image_directory = os.path.join(BASE_DIR, "assets")
    try:
        return send_from_directory(image_directory, filename)
    except FileNotFoundError:
        return jsonify({"error": "Image not found"}), 404

@api_bp.route('/menu', methods=['GET'])
@require_auth
def get_menu():
    worker = current_app.worker
    try:
        menu_data = worker.data_manager.get_menu_with_categories()
        
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

@api_bp.route('/nueva-orden', methods=['POST'])
@require_auth
def recibir_orden():
    worker = current_app.worker
    orden = request.json
    
    is_valid, error_msg = worker._validate_order_items(orden)
    if not is_valid:
        return jsonify({"error": "Item Agotado", "mensaje": error_msg}), 400
    
    order_id = orden.get("order_id")
    if worker.data_manager.check_duplicate_order_id(order_id):
        return jsonify({"status": "ok_duplicate"}), 200
    
    logger.info(f"Nueva orden recibida vía API: {order_id}")
    worker.nueva_orden_recibida.emit(orden) 
    worker.socketio.emit('kds_update', {'destino': 'all'})

    return jsonify({"status": "ok_new"}), 200

@api_bp.route('/api/split-order', methods=['POST'])
@require_auth
def split_order_endpoint():
    worker = current_app.worker
    data = request.json
    mesa_key = data.get('mesa_key')
    items = data.get('items') 
    
    if not mesa_key or not items:
        return jsonify({"error": "Datos incompletos"}), 400
        
    success = worker.data_manager.split_order(mesa_key, items)
    
    if success:
        logger.info(f"Cuenta separada exitosamente en Mesa {mesa_key}")
        # Acceso directo al helper de estado del worker si es posible, o duplicamos la lógica
        worker.socketio.emit('mesas_actualizadas', worker.data_manager.get_active_orders_caja())
        worker.ordenes_modificadas.emit() 
        return jsonify({"status": "success"}), 200
    else:
        logger.error(f"Fallo al separar cuenta en Mesa {mesa_key}")
        return jsonify({"error": "Error al dividir cuenta"}), 500

@api_bp.route('/employees', methods=['GET'])
@require_auth
def get_employees():
    worker = current_app.worker
    employees_full = worker.data_manager.get_employees() 
    if employees_full is None:
        return jsonify({"error": "No se pudo cargar la lista de empleados"}), 500
    
    employee_list = [
        {"id": emp.get("id_empleado"), "nombre": emp.get("nombre")}
        for emp in employees_full
        if emp.get("id_empleado") and emp.get("nombre") 
    ]
    return jsonify(employee_list)

@api_bp.route('/estado-mesas', methods=['GET'])
@require_auth
def get_estado_mesas():
    worker = current_app.worker
    try:
        caja_data = worker.data_manager.get_active_orders_caja()
        return jsonify(caja_data)
    except Exception as e:
        logger.error(f"Error obteniendo estado mesas: {e}")
        return jsonify({"error": "No se pudo cargar el estado de las mesas"}), 500

@api_bp.route('/trigger_update', methods=['POST'])
@require_auth
def trigger_update():
    worker = current_app.worker
    data = request.json
    event_name = data.get('event')
    payload_data = data.get('data') 
    
    logger.info(f"Retransmitiendo evento: {event_name}")
    
    if event_name == 'mesas_actualizadas':
        time.sleep(0.1) 
        table_state_payload = worker.data_manager.get_active_orders_caja()
        worker.socketio.emit('mesas_actualizadas', table_state_payload)
        
    elif event_name == 'menu_actualizado':
        worker.socketio.emit('menu_actualizado', {'mensaje': 'Menú cambiado'})
    
    else:
        if payload_data:
            worker.socketio.emit(event_name, payload_data)
        else:
            worker.socketio.emit(event_name)

    return jsonify({"status": "emitted"}), 200

@api_bp.route('/api/cancel-order', methods=['POST'])
@require_auth
def cancel_order_endpoint():
    worker = current_app.worker
    data = request.json
    mesa_key = data.get('mesa_key')
    
    if not mesa_key: return jsonify({"error": "Falta mesa_key"}), 400
    
    success = worker.data_manager.cancel_order_by_key(mesa_key)
    
    if success:
        logger.info(f"Orden cancelada manualmente: Mesa {mesa_key}")
        worker.socketio.emit('mesas_actualizadas', worker.data_manager.get_active_orders_caja())
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "No se pudo cancelar (¿Tiene productos?)"}), 400

@api_bp.route('/api/remove-items', methods=['POST'])
@require_auth
def remove_items_endpoint():
    worker = current_app.worker
    data = request.json
    mesa_key = data.get('mesa_key')
    items = data.get('items')
    
    if not mesa_key or not items:
        return jsonify({"error": "Datos incompletos"}), 400
        
    success = worker.data_manager.remove_items_from_order(mesa_key, items)
    
    if success:
        logger.info(f"Items eliminados de Mesa {mesa_key}")
        worker.socketio.emit('mesas_actualizadas', worker.data_manager.get_active_orders_caja())
        worker.socketio.emit('kds_update', {'destino': 'cocina'})
        worker.socketio.emit('kds_update', {'destino': 'barra'})
        worker.ordenes_modificadas.emit() 
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "No se pudieron eliminar"}), 400

# --- Biométrico ---

@api_bp.route('/api/biometric/status', methods=['GET'])
def biometric_status():
    worker = current_app.worker
    if worker.enroll_mode_active:
        return jsonify({"mode": "enroll"})
    
    if worker.clear_mode_active:
        return jsonify({"mode": "clear"})
        
    return jsonify({"mode": "scan"})

@api_bp.route('/api/biometric/enroll-success', methods=['POST'])
def biometric_enroll_success():
    worker = current_app.worker
    data = request.json
    finger_id = data.get('finger_id')
    worker.last_enrolled_id = finger_id

    logger.info(f"ESP32 reporta nueva huella registrada: ID {finger_id}")
    
    worker.enroll_mode_active = False
    worker.socketio.emit('fingerprint_registered', {'finger_id': finger_id})
    
    return jsonify({"status": "ok"})

@api_bp.route('/api/biometric/check-enroll-status', methods=['GET'])
def check_enroll():
    worker = current_app.worker
    if worker.last_enrolled_id is not None:
        fid = worker.last_enrolled_id
        worker.last_enrolled_id = None
        worker.enroll_status = {"step": 0, "message": "Esperando inicio..."}
        return jsonify({"status": "done", "finger_id": fid})
    
    return jsonify({
        "status": "in_progress", 
        "step": worker.enroll_status['step'],
        "message": worker.enroll_status['message']
    })

@api_bp.route('/api/biometric/attendance', methods=['POST'])
def biometric_attendance():
    worker = current_app.worker
    data = request.json
    finger_id = data.get('finger_id')
    
    empleado = worker.data_manager.get_employee_by_fingerprint(finger_id)
    if not empleado:
        return jsonify({"status": "error", "message": "Huella no vinculada"}), 404
        
    emp_id = empleado['id_empleado']
    last_event = worker.data_manager.get_last_attendance_event(emp_id)
    
    if last_event:
        last_ts = datetime.datetime.fromisoformat(last_event['timestamp'])
        now = datetime.datetime.now()
        diff_seconds = (now - last_ts).total_seconds()
        
        if diff_seconds < 3:
            logger.warning(f"Anti-rebote activado para {empleado['nombre']} (Intento duplicado en {int(diff_seconds)}s)")
            return jsonify({"status": "ignored", "message": "Registro muy seguido"}), 200

    tipo = "salida" if last_event and last_event['tipo'] == 'entrada' else "entrada"
    
    worker._registrar_evento(emp_id, tipo)
    
    logger.info(f"Asistencia biométrica: {empleado['nombre']} ({tipo})")
    return jsonify({"status": "success", "nombre": empleado['nombre'], "tipo": tipo})

@api_bp.route('/api/biometric/start-enroll', methods=['POST'])
@require_auth
def start_enroll_mode():
        worker = current_app.worker
        worker.enroll_mode_active = True
        worker.last_enrolled_id = None
        worker.enroll_status = {"step": 0, "message": "Pon el dedo en el sensor..."} 
        logger.info("Modo enrolamiento activado.")
        return jsonify({"status": "waiting_for_finger"})

@api_bp.route('/api/biometric/start-clear', methods=['POST'])
@require_auth
def start_clear_mode():
    worker = current_app.worker
    logger.warning("Solicitud de formateo de sensor recibida.")
    worker.clear_mode_active = True
    return jsonify({"status": "waiting_for_sensor_wipe"})

@api_bp.route('/api/biometric/clear-success', methods=['POST'])
def biometric_clear_success():
    worker = current_app.worker
    logger.info("El ESP32 confirma: Sensor biométrico formateado.")
    worker.clear_mode_active = False
    
    try:
        worker.data_manager.execute("UPDATE empleados SET fingerprint_id = NULL;")
        logger.info("Base de datos local sincronizada (Huellas desvinculadas).")
    except Exception as e:
        logger.error(f"Error limpiando BD local: {e}")

    return jsonify({"status": "ok"})

@api_bp.route('/api/send-kds-message', methods=['POST'])
@require_auth
def send_kds_message():
    worker = current_app.worker
    data = request.json
    
    mesa_key = data.get('mesa_key')
    mensaje = data.get('mensaje')
    destino = data.get('destino')
    
    if not mesa_key or not mensaje or not destino:
        return jsonify({"error": "Datos incompletos"}), 400
        
    logger.info(f"Mensaje KDS recibido para {destino}: {mensaje} (Mesa {mesa_key})")
    
    worker.socketio.emit('kds_message_alert', {
        'mesa_key': mesa_key,
        'mensaje': mensaje,
        'destino': destino,
        'timestamp': datetime.datetime.now().isoformat()
    })
    
    return jsonify({"status": "sent"}), 200

@api_bp.route('/api/update-item-note', methods=['POST'])
@require_auth
def update_item_note_endpoint():
    worker = current_app.worker
    data = request.json
    
    id_detalle = data.get('id_detalle')
    nota = data.get('nota')
    
    if not id_detalle:
        return jsonify({"error": "Faltan datos"}), 400
        
    success = worker.data_manager.update_item_note(id_detalle, nota)
    
    if success:
        logger.info(f"Nota actualizada para item {id_detalle}: {nota}")
        worker.socketio.emit('kds_update', {'destino': 'all'})
        worker.socketio.emit('mesas_actualizadas', worker.data_manager.get_active_orders_caja())
        worker.ordenes_modificadas.emit()
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"error": "Error BD"}), 500