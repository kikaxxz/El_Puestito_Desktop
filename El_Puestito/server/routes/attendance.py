from flask import Blueprint, jsonify, request, current_app
from logger_setup import setup_logger
from server.routes.kds import require_auth
from src.services.attendance_service import attendance_service
from src.database.repositories.employees import employee_repo

logger = setup_logger()
attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/registrar', methods=['POST'])
@require_auth
def registrar_asistencia_movil():
    try:
        worker = current_app.worker
        data = request.json
        if not data or 'employee_id' not in data or 'deviceId' not in data: return jsonify({"error": "Datos incompletos"}), 400
        employee_id = data['employee_id']
        device_id = data['deviceId']
        
        empleado = employee_repo.get_employee_by_id(employee_id)
        if not empleado: return jsonify({"error": "not_found"}), 404
        
        if not empleado.get("deviceId"):
            employee_repo.link_device_to_employee(employee_id, device_id)
            worker._registrar_evento(employee_id, "entrada")
            return jsonify({"status": "success", "message": "Dispositivo vinculado y entrada marcada"}), 201
        elif empleado.get("deviceId") != device_id:
            return jsonify({"error": "device_mismatch"}), 403
        
        import datetime
        last_event = attendance_service.get_last_attendance_event(employee_id)
        if last_event:
            last_ts = datetime.datetime.fromisoformat(last_event['timestamp'])
            now = datetime.datetime.now()
            diff = (now - last_ts).total_seconds()
            if diff < 3: return jsonify({"status": "ignored", "message": f"Espera {3 - int(diff)}s antes de marcar de nuevo."}), 200

        tipo = "salida" if last_event and last_event['tipo'] == 'entrada' else "entrada"
        worker._registrar_evento(employee_id, tipo)
        return jsonify({"status": "success", "message": f"{tipo.capitalize()} registrada"}), 200
    except Exception as e:
        logger.error(f"Error en registrar_asistencia_movil: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
