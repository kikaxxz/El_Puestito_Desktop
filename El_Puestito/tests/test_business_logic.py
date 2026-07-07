import pytest
import datetime
from src.database.connection import db_manager
from src.services.payroll_service import PayrollService
from src.database.repositories.menu import menu_repo

@pytest.fixture
def payroll_service(app_controller):
    return PayrollService(app_controller)

def test_payroll_multiple_shifts(clean_db):
    """
    Prueba que la logica de nomina calcule correctamente multiples turnos en un solo dia para un empleado.
    """
    payroll_service = PayrollService()
    
    # Insertar empleado Mesero (pago: 0.5/min)
    db_manager.execute("INSERT INTO empleados (id_empleado, nombre, rol) VALUES ('EMP1', 'Juan', 'Mesero')")
    
    # Insertar eventos: Turno 1 (60 min)
    db_manager.execute("INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES ('EMP1', '2026-01-02T10:00:00.000000', 'entrada')")
    db_manager.execute("INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES ('EMP1', '2026-01-02T11:00:00.000000', 'salida')")
    
    # Turno 2 (120 min)
    db_manager.execute("INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES ('EMP1', '2026-01-02T13:00:00.000000', 'entrada')")
    db_manager.execute("INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES ('EMP1', '2026-01-02T15:00:00.000000', 'salida')")
    
    # Para el test, hacemos mock de la configuracion
    from src.config.config_service import config_service
    conf = config_service.get_config()
    conf["roles_pago"] = {"Mesero": {"pago_minuto": 0.5}}
    conf["horarios_y_margenes"] = {"salida_oficial": "18:00"}
    config_service.save_config(conf)
    
    reporte, _ = payroll_service.calculate_payroll("2026-01-02", "2026-01-02")
    
    # Validar resultados
    assert len(reporte) == 1
    emp_report = reporte['EMP1']
    
    # Total minutos: 60 + 120 = 180 min
    # Total pago = 180 * 0.5 = 90
    assert emp_report['total_reg_mins'] == 180
    assert emp_report['total_pay'] == 90.0
