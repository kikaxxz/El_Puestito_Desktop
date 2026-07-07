from flask import Blueprint, jsonify, render_template, request, session, current_app, redirect, url_for
import time
from functools import wraps
from logger_setup import setup_logger

logger = setup_logger()
auth_bp = Blueprint('auth', __name__)
kds_bp = Blueprint('kds', __name__)

failed_attempts = {}

def require_kds_session(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS': return f(*args, **kwargs)
        destino_url = kwargs.get('destino') or (request.json and request.json.get('destino'))
        session_destino = session.get('kds_access')
        if not session_destino or (destino_url and session_destino != destino_url):
            logger.warning(f"Intento de acceso KDS no autorizado desde {request.remote_addr}")
            return jsonify({"error": "Unauthorized", "message": "Sesion invalida o destino incorrecto"}), 403
        return f(*args, **kwargs)
    return decorated

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS': return f(*args, **kwargs)
        worker = current_app.worker
        token = request.headers.get('X-API-KEY')
        if token != worker.API_KEY:
            logger.warning(f"Intento de acceso no autorizado desde {request.remote_addr}")
            return jsonify({"error": "Unauthorized", "message": "Falta API Key valida"}), 401
        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/')
def index():
    return render_template('login.html')

@kds_bp.route('/kds/<destino>')
def kds_view(destino):
    if destino not in ['cocina', 'barra']: return "Destino no valido", 404
    if session.get('kds_access') != destino: return redirect(url_for('auth.index'))
    return render_template('kds_view.html', destino=destino)

@auth_bp.route('/api/validar-pin', methods=['POST'])
def validar_pin():
    ip = request.remote_addr
    now = time.time()
    if ip in failed_attempts:
        attempts, last_time = failed_attempts[ip]
        if attempts >= 5 and now - last_time < 60:
            return jsonify({"status": "error", "message": "Demasiados intentos"}), 429
        elif now - last_time >= 60:
            del failed_attempts[ip]
    try:
        worker = current_app.worker
        data = request.json
        pin = data.get('pin')
        destino = worker.PINS_WEB_MAP.get(str(pin))
        if destino:
            logger.info(f"Acceso KDS web autorizado para: {destino}")
            session['kds_access'] = destino 
            if ip in failed_attempts: del failed_attempts[ip]
            return jsonify({"status": "success", "redirect": f"/kds/{destino}"})
        else:
            logger.warning("Intento de PIN incorrecto en KDS web")
            failed_attempts[ip] = (failed_attempts.get(ip, (0, now))[0] + 1, now)
            return jsonify({"status": "error", "message": "PIN Incorrecto"}), 401
    except Exception as e:
        logger.error(f"Error en validar_pin: {e}")
        return jsonify({"status": "error", "message": "Error interno"}), 500

@auth_bp.route('/api/logout', methods=['POST'])
def logout_kds():
    session.pop('kds_access', None)
    return jsonify({"status": "success"})

@kds_bp.route('/api/kds-orders/<destino>', methods=['GET'])
@require_kds_session
def get_kds_orders(destino):
    try:
        from src.services.order_service import order_service
        ordenes = order_service.get_kds_orders(destino)
        return jsonify(ordenes)
    except Exception as e:
        logger.error(f"Error obteniendo ordenes KDS para {destino}: {e}")
        return jsonify({"error": "Error interno"}), 500

@kds_bp.route('/api/kds-complete', methods=['POST'])
@require_kds_session
def complete_kds_order():
    try:
        worker = current_app.worker
        from src.services.order_service import order_service
        data = request.json
        mesa_key = data.get('mesa_key')
        destino = data.get('destino')
        
        order_service.mark_order_ready(mesa_key, destino)
        
        worker.socketio.emit('kds_update', {'destino': destino}, to=destino)
        worker.kds_estado_cambiado.emit(destino)
        worker.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
        
        mensaje_alerta = f"Mesa {mesa_key}: Pedido de {destino} listo"
        worker.socketio.emit('alerta_orden_lista', {'mesa_key': mesa_key, 'destino': destino, 'mensaje': mensaje_alerta})
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Error completando orden KDS: {e}")
        return jsonify({"status": "error", "message": "Error interno"}), 500

@kds_bp.route('/api/send-kds-message', methods=['POST'])
@require_auth
def send_kds_message():
    try:
        worker = current_app.worker
        data = request.json
        mesa_key = data.get('mesa_key')
        mensaje = data.get('mensaje')
        destino = data.get('destino')
        if not mesa_key or not mensaje or not destino: return jsonify({"error": "Datos incompletos"}), 400
        logger.info(f"Mensaje KDS recibido para {destino}: {mensaje} (Mesa {mesa_key})")
        
        from datetime import datetime
        worker.socketio.emit('kds_message_alert', {
            'mesa_key': mesa_key, 'mensaje': mensaje, 'destino': destino, 'timestamp': datetime.now().isoformat()
        }, to=destino if destino != 'all' else None)
        if destino == 'all':
            worker.socketio.emit('kds_message_alert', {'mesa_key': mesa_key, 'mensaje': mensaje, 'destino': destino, 'timestamp': datetime.now().isoformat()}, to='cocina')
            worker.socketio.emit('kds_message_alert', {'mesa_key': mesa_key, 'mensaje': mensaje, 'destino': destino, 'timestamp': datetime.now().isoformat()}, to='barra')
        
        return jsonify({"status": "sent"}), 200
    except Exception as e:
        logger.error(f"Error en send_kds_message: {e}")
        return jsonify({"error": "Error interno"}), 500
