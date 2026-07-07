from src.database.repositories.attendance import attendance_repo
from logger_setup import setup_logger
import datetime

logger = setup_logger()

class AttendanceService:
    def add_attendance_event(self, employee_id, event_type, timestamp=None):
        if not timestamp:
            timestamp = datetime.datetime.now().isoformat()
        return attendance_repo.add_attendance_event(employee_id, event_type, timestamp)
        
    def get_attendance_history_range(self, start_date, end_date):
        return attendance_repo.get_attendance_history_range(start_date, end_date)
        
    def get_last_attendance_event(self, employee_id):
        return attendance_repo.get_last_attendance_event(employee_id)
        
    def get_events_for_today(self):
        return attendance_repo.get_events_for_today()

attendance_service = AttendanceService()
