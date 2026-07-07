from flask import Blueprint, jsonify, request, current_app
from logger_setup import setup_logger
from server.routes.kds import require_auth
from src.database.repositories.employees import employee_repo
import datetime

logger = setup_logger()
biometric_bp = Blueprint('biometric', __name__)

@biometric_bp.route('/api/biometric/update-progress', methods=['POST'])
@require_auth
def update_enroll_progress():
    try:
        worker = current_app.worker
        data = request.json
        worker.enroll_status = {"step": data.get('step'), "message": data.get('message')}
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/status', methods=['GET'])
@require_auth
def biometric_status():
    try:
        worker = current_app.worker
        if worker.enroll_mode_active: return jsonify({"mode": "enroll"})
        if worker.clear_mode_active: return jsonify({"mode": "clear"})
        return jsonify({"mode": "scan"})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/enroll-success', methods=['POST'])
@require_auth
def biometric_enroll_success():
    try:
        worker = current_app.worker
        finger_id = request.json.get('finger_id')
        worker.last_enrolled_id = finger_id
        worker.enroll_mode_active = False
        worker.socketio.emit('fingerprint_registered', {'finger_id': finger_id})
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/check-enroll-status', methods=['GET'])
@require_auth
def check_enroll():
    try:
        worker = current_app.worker
        if worker.last_enrolled_id is not None:
            fid = worker.last_enrolled_id
            worker.last_enrolled_id = None
            worker.enroll_status = {"step": 0, "message": "Esperando inicio..."}
            return jsonify({"status": "done", "finger_id": fid})
        return jsonify({"status": "in_progress", "step": worker.enroll_status.get('step', 0), "message": worker.enroll_status.get('message', '')})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/attendance', methods=['POST'])
@require_auth
def biometric_attendance():
    try:
        worker = current_app.worker
        finger_id = request.json.get('finger_id')
        empleado = employee_repo.get_employee_by_fingerprint(finger_id)
        if not empleado: return jsonify({"status": "error", "message": "Huella no vinculada"}), 404
            
        emp_id = empleado['id_empleado']
        from src.services.attendance_service import attendance_service
        last_event = attendance_service.get_last_attendance_event(emp_id)
        if last_event:
            diff = (datetime.datetime.now() - datetime.datetime.fromisoformat(last_event['timestamp'])).total_seconds()
            if diff < 3: return jsonify({"status": "ignored", "message": "Registro muy seguido"}), 200

        tipo = "salida" if last_event and last_event['tipo'] == 'entrada' else "entrada"
        worker._registrar_evento(emp_id, tipo)
        return jsonify({"status": "success", "nombre": empleado['nombre'], "tipo": tipo})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/start-enroll', methods=['POST'])
@require_auth
def start_enroll_mode():
    try:
        worker = current_app.worker
        worker.enroll_mode_active = True
        worker.last_enrolled_id = None
        worker.enroll_status = {"step": 0, "message": "Pon el dedo en el sensor..."} 
        return jsonify({"status": "waiting_for_finger"})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/start-clear', methods=['POST'])
@require_auth
def start_clear_mode():
    try:
        worker = current_app.worker
        worker.clear_mode_active = True
        return jsonify({"status": "waiting_for_sensor_wipe"})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@biometric_bp.route('/api/biometric/clear-success', methods=['POST'])
@require_auth
def biometric_clear_success():
    try:
        worker = current_app.worker
        worker.clear_mode_active = False
        from src.database.connection import db_manager
        db_manager.execute("UPDATE empleados SET fingerprint_id = NULL;")
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500
