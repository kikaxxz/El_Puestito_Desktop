import datetime
from src.config.config_service import config_service
from src.database.repositories.attendance import attendance_repo
from src.database.repositories.employees import employee_repo
from logger_setup import setup_logger

logger = setup_logger()

class PayrollService:
    def calculate_payroll(self, start_date_str, end_date_str):
        start_date = datetime.date.fromisoformat(start_date_str)
        end_date = datetime.date.fromisoformat(end_date_str)
        end_date_exclusive = end_date + datetime.timedelta(days=1)
        
        config = config_service.get_config()
        roles_pago = config.get("roles_pago", {})
        horarios = config.get("horarios_y_margenes", {})
        politicas = config.get("politicas_pago_extra", {})
        
        try:
            sal_str = horarios.get("salida_oficial", "17:00")
            h_sal, m_sal = map(int, sal_str.split(':'))
        except:
            h_sal, m_sal = 17, 0
            
        ot_multiplier = politicas.get("multiplicador_hora_extra", 2.0)
        feriados_info = politicas.get("feriados", {})
        holidays_list = feriados_info.get("fechas", [])
        holiday_mult = feriados_info.get("multiplicador", 2.0)

        employees = employee_repo.get_employees()
        employees_dict = {emp['id_empleado']: emp for emp in employees}
        
        attendance_history = attendance_repo.get_attendance_history_range(
            start_date.isoformat(), 
            end_date_exclusive.isoformat()
        )
        
        if not attendance_history:
            return {}, {}
            
        payroll_results = {}
        payroll_daily_details = {}
        valid_entries = []
        
        for entry in attendance_history:
            try:
                ts = datetime.datetime.fromisoformat(entry['timestamp'])
                valid_entries.append({
                    "employee_id": entry['id_empleado'],
                    "timestamp": ts, 
                    "type": entry['tipo']
                })
            except (ValueError, KeyError): 
                continue
                
        valid_entries.sort(key=lambda x: (x['employee_id'], x['timestamp']))
        last_entry_time = None
        
        for entry in valid_entries:
            emp_id = entry['employee_id']
            ts = entry['timestamp']
            entry_type = entry['type']
            day_str = ts.date().isoformat()
            
            if emp_id not in payroll_results:
                payroll_results[emp_id] = {"total_reg_mins": 0, "total_ot_mins": 0, "total_pay": 0.0, "total_reg_pay": 0.0, "total_ot_pay": 0.0}
            if emp_id not in payroll_daily_details:
                payroll_daily_details[emp_id] = {}
            if day_str not in payroll_daily_details[emp_id]:
                payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0, "is_holiday": False}
            
            day_month_str = ts.strftime("%d-%m")
            is_holiday = day_month_str in holidays_list
            payroll_daily_details[emp_id][day_str]["is_holiday"] = is_holiday

            if entry_type == "entrada":
                if payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                    payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                last_entry_time = ts 
                
            elif entry_type == "salida" and last_entry_time is not None:
                shift_day_str = last_entry_time.date().isoformat()
                total_minutes_shift = (ts - last_entry_time).total_seconds() / 60
                
                employee_info = employees_dict.get(emp_id)
                rol = employee_info.get("rol") if employee_info else None
                rate_info = roles_pago.get(rol) if rol else None
                
                if rate_info and "pago_minuto" in rate_info and total_minutes_shift > 0:
                    rate_per_minute = rate_info["pago_minuto"]
                    
                    overtime_start_time = last_entry_time.replace(hour=h_sal, minute=m_sal, second=0, microsecond=0)
                    
                    regular_minutes_shift = 0
                    overtime_minutes_shift = 0
                    
                    if ts <= overtime_start_time:
                        regular_minutes_shift = total_minutes_shift
                    elif last_entry_time >= overtime_start_time:
                        overtime_minutes_shift = total_minutes_shift
                    else: 
                        regular_duration = overtime_start_time - last_entry_time
                        regular_minutes_shift = regular_duration.total_seconds() / 60
                        overtime_duration = ts - overtime_start_time
                        overtime_minutes_shift = overtime_duration.total_seconds() / 60
                        
                    shift_day_month_str = last_entry_time.strftime("%d-%m")
                    is_holiday_shift = shift_day_month_str in holidays_list
                    current_shift_mult = holiday_mult if is_holiday_shift else 1.0

                    reg_pay_shift = regular_minutes_shift * rate_per_minute * current_shift_mult
                    ot_pay_shift = overtime_minutes_shift * rate_per_minute * ot_multiplier * current_shift_mult
                    shift_pay = reg_pay_shift + ot_pay_shift
                    
                    payroll_results[emp_id]["total_reg_mins"] += regular_minutes_shift
                    payroll_results[emp_id]["total_ot_mins"] += overtime_minutes_shift
                    payroll_results[emp_id]["total_reg_pay"] += reg_pay_shift 
                    payroll_results[emp_id]["total_ot_pay"] += ot_pay_shift   
                    payroll_results[emp_id]["total_pay"] += shift_pay       
                    
                    if shift_day_str not in payroll_daily_details[emp_id]:
                        payroll_daily_details[emp_id][shift_day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0, "is_holiday": is_holiday_shift}
                        
                    payroll_daily_details[emp_id][shift_day_str]["reg_mins"] += regular_minutes_shift
                    payroll_daily_details[emp_id][shift_day_str]["ot_mins"] += overtime_minutes_shift
                    payroll_daily_details[emp_id][shift_day_str]["pay"] += shift_pay
                    payroll_daily_details[emp_id][shift_day_str]["last_exit"] = ts 
                    last_entry_time = None 
                else: 
                    payroll_daily_details[emp_id][shift_day_str]["last_exit"] = ts 
                    last_entry_time = None
                    
            elif entry_type == "salida" and last_entry_time is None:
                pass

        return payroll_results, payroll_daily_details

payroll_service = PayrollService()
