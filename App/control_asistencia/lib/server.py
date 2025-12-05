from flask import Flask, request, jsonify
import json
import os
from functools import wraps

app = Flask(__name__)

ASISTENCIA_FILE_PATH = r"C:\Proyectos\El_Puestito\assets\asistencia.json"
API_KEY = "puestito_seguro_2025"

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-KEY') != API_KEY:
            return jsonify({"error": "Unauthorized", "message": "API Key invalida o ausente"}), 401
        return f(*args, **kwargs)
    return decorated_function

def load_employee_data():
    if not os.path.exists(ASISTENCIA_FILE_PATH):
        return []
    try:
        with open(ASISTENCIA_FILE_PATH, "r", encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return []

def save_employee_data(data):
    try:
        with open(ASISTENCIA_FILE_PATH, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError:
        return False

@app.route('/employees', methods=['GET'])
@require_api_key
def get_employees():
    employees = load_employee_data()
    public_list = [{"id": emp["id"], "nombre": emp["nombre"]} for emp in employees]
    return jsonify(public_list), 200

@app.route('/registrar', methods=['POST'])
@require_api_key
def registrar_asistencia():
    data = request.get_json()

    if not data or 'employee_id' not in data or 'deviceId' not in data:
        return jsonify({"error": "Datos incompletos"}), 400

    employee_id = data['employee_id']
    device_id = data['deviceId']

    employees = load_employee_data()
    
    if not employees:
        return jsonify({"error": "Error interno del servidor"}), 500

    empleado_encontrado = None
    
    for emp in employees:
        if emp.get("deviceId") and emp.get("deviceId") == device_id and emp.get("id") != employee_id:
            return jsonify({
                "error": "device_taken",
                "message": f"Dispositivo ya registrado por {emp.get('nombre')}."
            }), 403 

        if emp.get("id") == employee_id:
            empleado_encontrado = emp
    
    if not empleado_encontrado:
        return jsonify({"error": "not_found", "message": "Empleado no encontrado."}), 404

    if empleado_encontrado.get("deviceId") is None:
        empleado_encontrado["deviceId"] = device_id
        
        if not save_employee_data(employees):
            return jsonify({"error": "Error interno al guardar"}), 500
        
        return jsonify({
            "status": "success",
            "message": f"Dispositivo vinculado a {empleado_encontrado['nombre']}."
        }), 201 

    elif empleado_encontrado.get("deviceId") == device_id:
        return jsonify({
            "status": "success",
            "message": f"Asistencia de {empleado_encontrado['nombre']} registrada."
        }), 200

    else:
        return jsonify({
            "error": "device_mismatch",
            "message": "Este dispositivo no coincide con el registrado."
        }), 403

if __name__ == '__main__':
    if not os.path.exists(ASISTENCIA_FILE_PATH):
        print(f"ADVERTENCIA: Archivo no encontrado en {ASISTENCIA_FILE_PATH}")
        
    app.run(host='0.0.0.0', port=5000, debug=True)