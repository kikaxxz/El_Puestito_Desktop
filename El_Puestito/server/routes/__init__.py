from flask import Blueprint

api_bp = Blueprint('api', __name__)

from .main import main_bp
from .kds import kds_bp, auth_bp
from .orders import orders_bp
from .attendance import attendance_bp
from .reports import reports_bp
from .biometric import biometric_bp

api_bp.register_blueprint(main_bp)
api_bp.register_blueprint(auth_bp)
api_bp.register_blueprint(kds_bp)
api_bp.register_blueprint(orders_bp)
api_bp.register_blueprint(attendance_bp)
api_bp.register_blueprint(reports_bp)
api_bp.register_blueprint(biometric_bp)
