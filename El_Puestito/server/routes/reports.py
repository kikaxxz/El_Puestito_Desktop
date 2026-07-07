from flask import Blueprint, jsonify, render_template, request, current_app
from logger_setup import setup_logger
import datetime

logger = setup_logger()
reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reportes-web')
def view_reportes():
    return render_template('reportes_dashboard.html')

@reports_bp.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    try:
        from src.services.order_service import order_service
        start_arg = request.args.get('start')
        end_arg = request.args.get('end')
        
        if start_arg and end_arg:
            try:
                start_dt = datetime.date.fromisoformat(start_arg)
                end_dt = datetime.date.fromisoformat(end_arg)
                if start_dt > end_dt: return jsonify({"error": "La fecha de inicio no puede ser posterior a la de fin"}), 400
            except ValueError:
                return jsonify({"error": "Formato de fecha invalido"}), 400
        
        tendencia = order_service.get_sales_history_range(start_arg, end_arg)
        hoy = datetime.date.today().isoformat()
        
        if start_arg and end_arg:
            from src.database.repositories.orders import order_repo
            top_items = order_repo.get_top_products_range(start_arg, end_arg)
        else:
            from src.database.repositories.orders import order_repo
            top_items = order_repo.get_top_products_range(hoy, hoy)

        top_platillos = {"nombres": [item['nombre'] for item in top_items], "cantidades": [item['cantidad_total'] for item in top_items]}
        total_hoy, _ = order_service.get_sales_report(hoy)
        
        return jsonify({"tendencia": tendencia, "top_productos": top_platillos, "resumen_hoy": {"total": total_hoy}})
    except Exception as e:
        logger.error(f"Error generando datos para graficas: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
