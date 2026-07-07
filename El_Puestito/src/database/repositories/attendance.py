from src.database.connection import db_manager
import sqlite3
import datetime
from logger_setup import setup_logger

logger = setup_logger()

class AttendanceRepository:
    def add_attendance_event(self, employee_id, event_type, timestamp):
        return db_manager.execute("INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);", (employee_id, timestamp, event_type))
        
    def get_attendance_history_range(self, start_date, end_date):
        return db_manager.fetchall("""
            SELECT e.nombre, e.rol, ev.timestamp, ev.tipo, ev.id_empleado
            FROM eventos_asistencia ev
            JOIN empleados e ON ev.id_empleado = e.id_empleado
            WHERE ev.timestamp BETWEEN ? AND ?
            ORDER BY ev.id_empleado, ev.timestamp;
            """, (start_date, end_date))
        
    def clear_all_attendance_history(self):
        return db_manager.execute("DELETE FROM eventos_asistencia;")

    def get_last_attendance_event(self, employee_id):
        return db_manager.fetchone("SELECT tipo, timestamp FROM eventos_asistencia WHERE id_empleado = ? ORDER BY timestamp DESC LIMIT 1;", (employee_id,))

    def add_attendance_events_batch(self, events_list):
        query = "INSERT INTO eventos_asistencia (id_empleado, timestamp, tipo) VALUES (?, ?, ?);"
        try:
            conn = db_manager.get_conn()
            cursor = conn.cursor()
            cursor.executemany(query, events_list)
            conn.commit()
            return True
        except sqlite3.Error as e: 
            logger.error(f"Error insertando eventos de asistencia en bloque: {e}")
            return False
    
    def get_events_for_today(self):
        today_str = datetime.date.today().isoformat()
        query = """
        SELECT id_empleado, tipo, MAX(timestamp) as last_timestamp
        FROM eventos_asistencia
        WHERE DATE(timestamp) = DATE(?)
        GROUP BY id_empleado, tipo
        ORDER BY last_timestamp;
        """
        return db_manager.fetchall(query, (today_str,))

attendance_repo = AttendanceRepository()
