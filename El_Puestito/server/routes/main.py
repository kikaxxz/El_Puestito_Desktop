from flask import Blueprint, jsonify, request, current_app, send_from_directory
from logger_setup import setup_logger
from server.routes.kds import require_auth
from src.path_manager import get_persistent_path, get_asset_path
import os
import json

logger = setup_logger()
main_bp = Blueprint('main', __name__)

@main_bp.route('/api/update-fcm', methods=['POST'])
@require_auth
def update_fcm_endpoint():
    try:
        data = request.json
        emp_id = data.get('employee_id')
        token = data.get('fcm_token')
        recibe_alertas = data.get('recibe_alertas', True)
        if not emp_id or not token: return jsonify({"error": "Faltan datos"}), 400
        from src.database.connection import db_manager
        db_manager.execute("UPDATE empleados SET fcm_token = ?, recibe_alertas = ? WHERE id_empleado = ?;", (token, int(recibe_alertas), emp_id))
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": "Error interno"}), 500

@main_bp.route('/shutdown', methods=['POST'])
@require_auth
def shutdown():
    return jsonify({"status": "shutdown_ignored_in_threading_mode"})

@main_bp.route('/configuracion', methods=['GET'])
@require_auth
def get_configuracion():
    try:
        config_path = get_persistent_path("config.json")
        with open(config_path, 'r') as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify({"error": "Error cargando config"}), 500

@main_bp.route('/images/<path:filename>')
def serve_image(filename):
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.ico'}
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions: return jsonify({"error": "Forbidden"}), 403
    try:
        from src.path_manager import resolve_image_path
        directory, resolved_filename = resolve_image_path(filename)
        return send_from_directory(directory, resolved_filename)
    except FileNotFoundError:
        return jsonify({"error": "Image not found"}), 404

@main_bp.route('/menu', methods=['GET'])
@require_auth
def get_menu():
    try:
        from src.database.repositories.menu import menu_repo
        menu_data = menu_repo.get_menu_with_categories()
        menu_filtrado = {"categorias": []}
        for categoria_original in menu_data.get("categorias", []):
            items_disponibles = [item for item in categoria_original.get("items", []) if item.get("disponible", True)]
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
        return jsonify({"error": "No se pudo cargar el menu"}), 500

@main_bp.route('/employees', methods=['GET'])
@require_auth
def get_employees():
    try:
        from src.database.repositories.employees import employee_repo
        employees_full = employee_repo.get_employees() 
        if employees_full is None: return jsonify({"error": "No se pudo cargar la lista de empleados"}), 500
        employee_list = [{"id": emp.get("id_empleado"), "nombre": emp.get("nombre")} for emp in employees_full if emp.get("id_empleado") and emp.get("nombre")]
        return jsonify(employee_list)
    except Exception:
        return jsonify({"error": "Error interno"}), 500
