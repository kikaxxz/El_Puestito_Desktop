from src.database.connection import db_manager
import sqlite3
from logger_setup import setup_logger

logger = setup_logger()

class EmployeeRepository:
    def get_employees(self):
        return db_manager.fetchall("SELECT * FROM empleados ORDER BY nombre;")

    def get_employee_by_id(self, employee_id):
        return db_manager.fetchone("SELECT * FROM empleados WHERE id_empleado = ?;", (employee_id,))

    def get_employee_by_device(self, device_id):
        return db_manager.fetchone("SELECT * FROM empleados WHERE deviceId = ?;", (device_id,))
        
    def add_employee(self, id, nombre, rol, fingerprint_id=None):
        return db_manager.execute(
            "INSERT INTO empleados (id_empleado, nombre, rol, fingerprint_id) VALUES (?, ?, ?, ?);", 
            (id, nombre, rol, fingerprint_id)
        )

    def update_employee(self, id_original, new_id, new_name, new_rol, fingerprint_id=None):
        return db_manager.execute(
            "UPDATE empleados SET id_empleado = ?, nombre = ?, rol = ?, fingerprint_id = ? WHERE id_empleado = ?;", 
            (new_id, new_name, new_rol, fingerprint_id, id_original)
        )
        
    def delete_employee(self, employee_id):
        try:
            return db_manager.execute("DELETE FROM empleados WHERE id_empleado = ?;", (employee_id,))
        except sqlite3.IntegrityError:
            logger.warning(f"No se puede borrar empleado {employee_id}, tiene historial.")
            return None

    def link_device_to_employee(self, employee_id, device_id):
        return db_manager.execute("UPDATE empleados SET deviceId = ? WHERE id_empleado = ?;", (device_id, employee_id))

    def link_fingerprint_to_employee(self, employee_id, fingerprint_id):
        try:
            db_manager.execute("UPDATE empleados SET fingerprint_id = NULL WHERE fingerprint_id = ?", (fingerprint_id,))
            return db_manager.execute("UPDATE empleados SET fingerprint_id = ? WHERE id_empleado = ?", (fingerprint_id, employee_id))
        except Exception as e:
            logger.error(f"Error vinculando huella: {e}")
            return False
            
    def get_employee_by_fingerprint(self, fingerprint_id):
        return db_manager.fetchone("SELECT * FROM empleados WHERE fingerprint_id = ?", (fingerprint_id,))

    def get_first_unlinked_employee(self):
        return db_manager.fetchone("SELECT * FROM empleados WHERE deviceId IS NULL OR deviceId = '' ORDER BY nombre LIMIT 1;")

employee_repo = EmployeeRepository()
