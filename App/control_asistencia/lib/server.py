from flask import Flask, request, jsonify
import datetime
import json
import os

app = Flask(__name__)

ASISTENCIA_FILE_PATH = r"C:\Proyectos\El_Puestito\assets\asistencia.json"


# --- FUNCIONES AUXILIARES ---

def load_employee_data():
    """Carga los datos de los empleados desde el JSON."""
    if not os.path.exists(ASISTENCIA_FILE_PATH):
        print("================================================")
        print(f"Error CRÍTICO: No se encuentra el archivo en:")
        print(ASISTENCIA_FILE_PATH)
        print("Asegúrate de que la ruta de 'ASISTENCIA_FILE_PATH' sea correcta.")
        print("================================================")
        return None # Devolvemos None para indicar un error
    try:
        with open(ASISTENCIA_FILE_PATH, "r", encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error al leer el JSON: {e}")
        return None # Devolvemos None para indicar un error

def save_employee_data(data):
    """Guarda los datos de los empleados en el JSON."""
    try:
        with open(ASISTENCIA_FILE_PATH, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error al guardar el archivo: {e}")
        return False

# --- RUTA PRINCIPAL ---

@app.route('/registrar', methods=['POST'])
def registrar_asistencia():
    data = request.get_json()
    print("-----------------------------------------")
    print(f"Datos recibidos: {data}")

    if not data or 'employee_id' not in data or 'deviceId' not in data:
        print("Error: Datos incompletos (falta employee_id o deviceId).")
        return jsonify({"error": "Datos incompletos"}), 400

    employee_id = data['employee_id']
    device_id = data['deviceId']

    employees = load_employee_data()
    
    # Si el archivo JSON no se pudo cargar, detenemos todo.
    if employees is None:
        print("Error: No se pudo cargar el archivo de empleados.")
        return jsonify({"error": "Error interno del servidor (no se pudo leer la BD)"}), 500

    empleado_encontrado = None
    
    # 1. Buscar al empleado Y verificar si el dispositivo ya está en uso
    for emp in employees:
        # Comprobamos si el deviceId existe (no es null) Y si coincide
        if emp.get("deviceId") and emp.get("deviceId") == device_id and emp.get("id") != employee_id:
            print(f"Error: Dispositivo {device_id} ya registrado por {emp.get('nombre')}.")
            return jsonify({
                "error": "device_taken",
                "message": f"Este dispositivo ya está registrado a nombre de: {emp.get('nombre')}. Contacte al administrador."
            }), 403 # 403 Forbidden (Prohibido)

        if emp.get("id") == employee_id:
            empleado_encontrado = emp
    
    # 2. Si no encontramos al empleado
    if not empleado_encontrado:
        print(f"Error: Empleado con ID {employee_id} no encontrado.")
        return jsonify({"error": "not_found", "message": "Empleado no encontrado en la base de datos."}), 404

    # 3. Lógica de registro/vinculación
    if empleado_encontrado.get("deviceId") is None:
        # --- ES EL PRIMER REGISTRO (VINCULACIÓN) ---
        print(f"Vinculando dispositivo {device_id} al empleado {empleado_encontrado['nombre']}...")
        empleado_encontrado["deviceId"] = device_id
        
        # Guardamos los datos actualizados en el JSON
        if not save_employee_data(employees):
            return jsonify({"error": "Error interno al guardar"}), 500
        
        print("Dispositivo vinculado y asistencia registrada.")
        # Le enviamos el mensaje de éxito a la app de Flutter
        return jsonify({
            "status": "success",
            "message": f"Dispositivo registrado a {empleado_encontrado['nombre']}. Asistencia marcada."
        }), 201 # 201 Creado (nuevo vínculo)

    elif empleado_encontrado.get("deviceId") == device_id:
        # --- ES UN REGISTRO NORMAL (El dispositivo coincide) ---
        print(f"Asistencia normal registrada para {empleado_encontrado['nombre']}.")
        
        # Le enviamos el mensaje de éxito a la app de Flutter
        return jsonify({
            "status": "success",
            "message": f"Asistencia de {empleado_encontrado['nombre']} registrada correctamente."
        }), 200 # 200 OK (registro normal)

    else:
        # --- INTENTO DE FRAUDE (El dispositivo no coincide) ---
        print(f"Error de Fraude: ID de empleado {employee_id} ({empleado_encontrado['nombre']}) intentó registrarse con un dispositivo diferente.")
        return jsonify({
            "error": "device_mismatch",
            "message": "Este dispositivo no coincide con el registrado para este empleado. Contacte al administrador."
        }), 403 # 403 Forbidden (Prohibido)

# Iniciar el servidor
if __name__ == '__main__':
    print("Iniciando servidor de asistencia inteligente...")
    # Esta comprobación se hace ahora en load_employee_data()
    # para que se ejecute en cada recarga del debug
    
    # Verificamos la ruta al iniciar
    if not os.path.exists(ASISTENCIA_FILE_PATH):
        print("================================================")
        print(f"ADVERTENCIA: No se encuentra el archivo JSON en:")
        print(ASISTENCIA_FILE_PATH)
        print("Asegúrate de que la ruta en 'ASISTENCIA_FILE_PATH' sea correcta.")
        print("================================================")
    else:
        print(f"Usando archivo de base de datos: {ASISTENCIA_FILE_PATH}")
        
    app.run(host='0.0.0.0', port=5000, debug=True)