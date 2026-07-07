from flask import Blueprint, jsonify, request, current_app
from logger_setup import setup_logger
from server.routes.kds import require_auth

logger = setup_logger()
orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/nueva-orden', methods=['POST'])
@require_auth
def recibir_orden():
    try:
        worker = current_app.worker
        orden = request.json
        from src.services.order_service import order_service
        
        order_id = orden.get("order_id")
        from src.database.repositories.orders import order_repo
        if order_repo.check_duplicate_order_id(order_id):
            return jsonify({"status": "ok_duplicate"}), 200
        
        logger.info(f"Procesando nueva orden sincronamente via API: {order_id}")
        try:
            nuevo_id = order_service.create_new_order(orden)
            worker.socketio.emit('kds_update', {'destino': 'all'}, to='cocina')
            worker.socketio.emit('kds_update', {'destino': 'all'}, to='barra')
            worker.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
            worker.ordenes_modificadas.emit() 
            return jsonify({"status": "ok_new"}), 200
        except ValueError as ve:
            logger.warning(f"Orden rechazada por validacion: {ve}")
            return jsonify({"error": "Item Agotado o Invalido", "mensaje": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error procesando nueva orden: {e}")
        return jsonify({"error": "Error interno al procesar la orden"}), 500

@orders_bp.route('/api/split-order', methods=['POST'])
@require_auth
def split_order_endpoint():
    try:
        worker = current_app.worker
        data = request.json
        from src.services.order_service import order_service
        mesa_key = data.get('mesa_key')
        items = data.get('items') 
        target_account_key = data.get('target_account_key')
        new_account_name = data.get('new_account_name')
        if not mesa_key or not items: return jsonify({"error": "Datos incompletos"}), 400
        success = order_service.split_order(mesa_key, items, target_account_key, new_account_name)
        if success:
            worker.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
            worker.ordenes_modificadas.emit() 
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "Error al dividir cuenta"}), 500
    except Exception as e:
        return jsonify({"error": "Error interno al procesar division"}), 500

@orders_bp.route('/estado-mesas', methods=['GET'])
@require_auth
def get_estado_mesas():
    from src.services.order_service import order_service
    try:
        caja_data = order_service.get_active_orders_caja()
        return jsonify(caja_data)
    except Exception as e:
        return jsonify({"error": "No se pudo cargar el estado de las mesas"}), 500

@orders_bp.route('/api/cancel-order', methods=['POST'])
@require_auth
def cancel_order_endpoint():
    try:
        worker = current_app.worker
        data = request.json
        from src.services.order_service import order_service
        mesa_key = data.get('mesa_key')
        if not mesa_key: return jsonify({"error": "Falta mesa_key"}), 400
        success = order_service.cancel_order(mesa_key)
        if success:
            worker.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "No se pudo cancelar"}), 400
    except Exception:
        return jsonify({"error": "Error interno"}), 500

@orders_bp.route('/api/remove-items', methods=['POST'])
@require_auth
def remove_items_endpoint():
    try:
        worker = current_app.worker
        data = request.json
        from src.services.order_service import order_service
        mesa_key = data.get('mesa_key')
        items = data.get('items')
        if not mesa_key or not items: return jsonify({"error": "Datos incompletos"}), 400
        success = order_service.remove_items_from_order(mesa_key, items)
        if success:
            worker.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
            worker.socketio.emit('kds_update', {'destino': 'cocina'}, to='cocina')
            worker.socketio.emit('kds_update', {'destino': 'barra'}, to='barra')
            worker.ordenes_modificadas.emit() 
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "No se pudieron eliminar"}), 400
    except Exception:
        return jsonify({"error": "Error interno"}), 500

@orders_bp.route('/api/update-item-note', methods=['POST'])
@require_auth
def update_item_note_endpoint():
    try:
        worker = current_app.worker
        data = request.json
        id_detalle = data.get('id_detalle')
        nota = data.get('nota')
        if not id_detalle: return jsonify({"error": "Faltan datos"}), 400
        from src.database.repositories.orders import order_repo
        success = order_repo.update_item_note(id_detalle, nota)
        if success:
            from src.services.order_service import order_service
            worker.socketio.emit('kds_update', {'destino': 'all'}, to='cocina')
            worker.socketio.emit('kds_update', {'destino': 'all'}, to='barra')
            worker.socketio.emit('mesas_actualizadas', order_service.get_active_orders_caja())
            worker.ordenes_modificadas.emit()
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "Error BD"}), 500
    except Exception:
        return jsonify({"error": "Error interno"}), 500
