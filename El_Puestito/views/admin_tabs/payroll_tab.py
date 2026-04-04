import os
import datetime
import random
from fpdf import FPDF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDateEdit, QTableWidget, QHeaderView, QTableWidgetItem, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, QDate
from logger_setup import setup_logger

logger = setup_logger()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PayrollTab(QWidget):
    def __init__(self, app_controller, config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.current_config = config
        self.employees_data = []
        self.payroll_daily_details = {}
        self.setup_ui()

    def setup_ui(self):
        payroll_layout = QVBoxLayout(self)
        payroll_layout.setContentsMargins(15, 15, 15, 15)
        payroll_layout.setSpacing(15)
        controls_hbox = QHBoxLayout()
        payroll_layout.addLayout(controls_hbox)
        controls_hbox.addWidget(QLabel("Desde:"))
        self.payroll_start_date = QDateEdit()
        self.payroll_start_date.setCalendarPopup(True)
        self.payroll_start_date.setDate(QDate.currentDate().addMonths(-1))
        controls_hbox.addWidget(self.payroll_start_date)
        controls_hbox.addWidget(QLabel("Hasta:"))
        self.payroll_end_date = QDateEdit()
        self.payroll_end_date.setCalendarPopup(True)
        self.payroll_end_date.setDate(QDate.currentDate())
        controls_hbox.addWidget(self.payroll_end_date)
        self.btn_calculate_payroll = QPushButton("Calcular Nómina")
        self.btn_calculate_payroll.setObjectName("orange_button")
        controls_hbox.addWidget(self.btn_calculate_payroll)
        controls_hbox.addStretch() 
        self.btn_export_pdf = QPushButton("Exportar PDF Seleccionado")
        self.btn_export_pdf.setObjectName("orange_button")
        self.btn_export_pdf.setEnabled(False) 
        controls_hbox.addWidget(self.btn_export_pdf)
        self.btn_generate_random = QPushButton("Generar Datos Aleatorios (Test)")
        controls_hbox.addWidget(self.btn_generate_random)
        payroll_layout.addWidget(QLabel("Resultados de Nómina:"))
        self.payroll_table = QTableWidget()
        self.payroll_table.setObjectName("employee_table")
        self.payroll_table.setColumnCount(7) 
        self.payroll_table.setHorizontalHeaderLabels([
            "Empleado", "Rol", "Hrs Reg.", "Hrs Ext.",
            "Pago Reg. (C$)", "Pago Ext. (C$)", "Pago Total (C$)"
        ])
        payroll_header = self.payroll_table.horizontalHeader()
        payroll_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        payroll_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        payroll_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        payroll_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        payroll_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        payroll_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        payroll_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.payroll_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.payroll_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        payroll_layout.addWidget(self.payroll_table)
        self.btn_calculate_payroll.clicked.connect(self.calculate_payroll)
        self.btn_export_pdf.clicked.connect(self.export_payroll_pdf)
        self.btn_generate_random.clicked.connect(self.generate_random_attendance)
        self.payroll_table.itemSelectionChanged.connect(self.update_export_button_state)

    def calculate_payroll(self):
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        start_date = start_date_q.toPyDate()
        end_date_inclusive = end_date_q.toPyDate()
        end_date_exclusive = end_date_q.toPyDate() + datetime.timedelta(days=1)
        logger.info(f"Calculando nómina desde {start_date} hasta {end_date_inclusive}...")
        payroll_rates = self.current_config.get("roles_pago", {})
        if not payroll_rates:
            QMessageBox.critical(self, "Error de Configuración", "No se encontraron tarifas de pago.")
            return
        self.employees_data = self.app_controller.get_todos_los_empleados()
        employees_dict = {emp['id_empleado']: emp for emp in self.employees_data}
        attendance_history_rows = self.app_controller.data_manager.get_attendance_history_range(
            start_date.isoformat(), 
            end_date_exclusive.isoformat()
        )
        if not attendance_history_rows:
            logger.info("No se encontró historial de asistencia en ese rango.")
            self.payroll_table.setRowCount(0)
            return
        payroll_results = {}
        self.payroll_daily_details = {}
        valid_entries = []
        for entry in attendance_history_rows:
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
            if emp_id not in self.payroll_daily_details:
                self.payroll_daily_details[emp_id] = {}
            if day_str not in self.payroll_daily_details[emp_id]:
                self.payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0}
            if entry_type == "entrada":
                if self.payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                    self.payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                last_entry_time = ts 
            elif entry_type == "salida" and last_entry_time is not None and last_entry_time.date() == ts.date():
                jornada_start_time = last_entry_time.replace(hour=12, minute=0, second=0, microsecond=0)
                start_time_for_calc = max(last_entry_time, jornada_start_time)
                if ts > start_time_for_calc: 
                    duration = ts - start_time_for_calc
                    total_minutes_shift = duration.total_seconds() / 60
                else:
                    total_minutes_shift = 0 
                employee_info = employees_dict.get(emp_id)
                rol = employee_info.get("rol") if employee_info else None
                rate_info = payroll_rates.get(rol) if rol else None
                if rate_info and "minuto" in rate_info and total_minutes_shift > 0:
                    rate_per_minute = rate_info["minuto"]
                    overtime_start_time = start_time_for_calc.replace(hour=22, minute=0, second=0, microsecond=0)
                    regular_minutes_shift = 0
                    overtime_minutes_shift = 0
                    if ts <= overtime_start_time:
                        regular_minutes_shift = total_minutes_shift
                    elif start_time_for_calc < overtime_start_time < ts:
                        regular_duration = overtime_start_time - start_time_for_calc
                        regular_minutes_shift = regular_duration.total_seconds() / 60
                        overtime_duration = ts - overtime_start_time
                        overtime_minutes_shift = overtime_duration.total_seconds() / 60
                    else: 
                        overtime_minutes_shift = total_minutes_shift
                    reg_pay_shift = regular_minutes_shift * rate_per_minute
                    ot_pay_shift = overtime_minutes_shift * rate_per_minute * 2
                    shift_pay = reg_pay_shift + ot_pay_shift
                    payroll_results[emp_id]["total_reg_mins"] += regular_minutes_shift
                    payroll_results[emp_id]["total_ot_mins"] += overtime_minutes_shift
                    payroll_results[emp_id]["total_reg_pay"] += reg_pay_shift 
                    payroll_results[emp_id]["total_ot_pay"] += ot_pay_shift   
                    payroll_results[emp_id]["total_pay"] += shift_pay       
                    self.payroll_daily_details[emp_id][day_str]["reg_mins"] += regular_minutes_shift
                    self.payroll_daily_details[emp_id][day_str]["ot_mins"] += overtime_minutes_shift
                    self.payroll_daily_details[emp_id][day_str]["pay"] += shift_pay
                    self.payroll_daily_details[emp_id][day_str]["last_exit"] = ts 
                    last_entry_time = None 
                else: 
                    if total_minutes_shift <= 0:
                        logger.info(f"No se calculó tiempo pagable para {emp_id} el {day_str} (salida antes/igual a 12PM).")
                    else:
                        logger.warning(f"No se pudo calcular pago para {emp_id} el {day_str} (rol '{rol}' o tarifa inválida).")
                    self.payroll_daily_details[emp_id][day_str]["last_exit"] = ts 
                    last_entry_time = None
            elif last_entry_time is not None and last_entry_time.date() != ts.date():
                last_entry_time = None
                if entry_type == "entrada": 
                    if day_str not in self.payroll_daily_details[emp_id]: 
                        self.payroll_daily_details[emp_id][day_str] = {"first_entry": None, "last_exit": None, "reg_mins": 0, "ot_mins": 0, "pay": 0.0}
                    if self.payroll_daily_details[emp_id][day_str]["first_entry"] is None:
                        self.payroll_daily_details[emp_id][day_str]["first_entry"] = ts
                    last_entry_time = ts
        self.payroll_table.setRowCount(0)
        self.payroll_table.setRowCount(len(payroll_results))
        row = 0
        for emp_id, results in payroll_results.items():
            employee_info = employees_dict.get(emp_id)
            if not employee_info: continue
            reg_hours = int(results["total_reg_mins"] // 60)
            reg_mins = int(results["total_reg_mins"] % 60)
            ot_hours = int(results["total_ot_mins"] // 60)
            ot_mins = int(results["total_ot_mins"] % 60)
            item_name = QTableWidgetItem(employee_info.get("nombre", "Desconocido"))
            item_rol = QTableWidgetItem(employee_info.get("rol", "N/A"))
            item_hrs_reg = QTableWidgetItem(f"{reg_hours:02d}:{reg_mins:02d}")
            item_hrs_ot = QTableWidgetItem(f"{ot_hours:02d}:{ot_mins:02d}")
            item_pay_reg = QTableWidgetItem(f"C$ {results['total_reg_pay']:.2f}") 
            item_pay_ot = QTableWidgetItem(f"C$ {results['total_ot_pay']:.2f}")   
            item_pay_total = QTableWidgetItem(f"C$ {results['total_pay']:.2f}")
            item_name.setData(Qt.ItemDataRole.UserRole, emp_id)
            item_hrs_reg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_hrs_ot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pay_reg.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pay_ot.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pay_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.payroll_table.setItem(row, 0, item_name)
            self.payroll_table.setItem(row, 1, item_rol)
            self.payroll_table.setItem(row, 2, item_hrs_reg)
            self.payroll_table.setItem(row, 3, item_hrs_ot)
            self.payroll_table.setItem(row, 4, item_pay_reg)
            self.payroll_table.setItem(row, 5, item_pay_ot)
            self.payroll_table.setItem(row, 6, item_pay_total)
            row += 1
        self.update_export_button_state()
        logger.info(f"Nómina calculada y mostrada para {len(payroll_results)} empleados. Detalles diarios guardados para PDF.")

    def export_payroll_pdf(self):
        selected_rows = self.payroll_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Seleccione un empleado de la tabla para exportar.")
            return
        selected_row_index = selected_rows[0].row()
        employee_name_item = self.payroll_table.item(selected_row_index, 0)
        employee_rol_item = self.payroll_table.item(selected_row_index, 1)
        if not employee_name_item or not employee_rol_item:
            QMessageBox.warning(self, "Error", "No se pudo obtener la información del empleado seleccionado.")
            return
        employee_name = employee_name_item.text()
        employee_rol = employee_rol_item.text()
        employee_id = employee_name_item.data(Qt.ItemDataRole.UserRole) 
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        start_date = start_date_q.toPyDate()
        end_date = end_date_q.toPyDate() 
        logger.info(f"Preparando PDF para {employee_name} (ID: {employee_id}) del {start_date} al {end_date}...")
        employee_daily_details = self.payroll_daily_details.get(employee_id, {})
        if not employee_daily_details:
            QMessageBox.information(self, "Sin Datos", f"No se encontraron registros de asistencia calculados para {employee_name} en el período seleccionado.")
            return
        default_filename = f"Nomina_{employee_name.replace(' ', '_')}_{start_date}_a_{end_date}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", default_filename, "PDF Files (*.pdf)")
        if not save_path:
            logger.info("Exportación cancelada por el usuario.")
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            logo_path = os.path.join(BASE_DIR,"Assets","logopdf.png") 
            if os.path.exists(logo_path):
                pdf.image(logo_path, x=5, y=5, w=50) 
                pdf.ln(20) 
            else:
                logger.warning(f"No se encontró el logo en {logo_path}")
                pdf.ln(20) 
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Reporte de Nómina", 0, 1, 'C')
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 7, f"Empleado: {employee_name}", 0, 1)
            pdf.cell(0, 7, f"Rol: {employee_rol}", 0, 1)
            pdf.cell(0, 7, f"Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}", 0, 1)
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(230, 230, 230) 
            col_widths = [25, 30, 30, 30, 30, 45] 
            headers = ["Fecha", "Entrada", "Salida", "Hrs Reg.", "Hrs Ext.", "Pago Diario (C$)"] 
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, 1, 0, 'C', fill=True)
            pdf.ln()
            pdf.set_font("Arial", size=10)
            total_period_reg_mins = 0
            total_period_ot_mins = 0
            total_period_pay = 0.0
            sorted_days = sorted(employee_daily_details.keys()) 
            for day_str in sorted_days:
                details = employee_daily_details[day_str] 
                fecha = datetime.date.fromisoformat(day_str).strftime('%d/%m/%y')
                entrada = details['first_entry'].strftime('%I:%M %p') if details['first_entry'] else "-"
                salida = details['last_exit'].strftime('%I:%M %p') if details['last_exit'] else "-"
                reg_h = int(details["reg_mins"] // 60)
                reg_m = int(details["reg_mins"] % 60)
                hrs_reg = f"{reg_h:02d}:{reg_m:02d}" if details['reg_mins'] > 0 or details['ot_mins'] > 0 else "-"
                ot_h = int(details["ot_mins"] // 60)
                ot_m = int(details["ot_mins"] % 60)
                hrs_ot = f"{ot_h:02d}:{ot_m:02d}" if details['ot_mins'] > 0 else "00:00"
                pago_diario = f"{details['pay']:.2f}" if details['reg_mins'] > 0 or details['ot_mins'] > 0 else "-"
                pdf.cell(col_widths[0], 7, fecha, 1, 0, 'C')
                pdf.cell(col_widths[1], 7, entrada, 1, 0, 'C')
                pdf.cell(col_widths[2], 7, salida, 1, 0, 'C')
                pdf.cell(col_widths[3], 7, hrs_reg, 1, 0, 'C')
                pdf.cell(col_widths[4], 7, hrs_ot, 1, 0, 'C')
                pdf.cell(col_widths[5], 7, pago_diario, 1, 0, 'R') 
                pdf.ln()
                if details['reg_mins'] > 0 or details['ot_mins'] > 0: 
                    total_period_reg_mins += details["reg_mins"]
                    total_period_ot_mins += details["ot_mins"]
                    total_period_pay += details["pay"]
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_widths[0] + col_widths[1] + col_widths[2], 8, "TOTALES:", 1, 0, 'R', fill=True)
            total_reg_h = int(total_period_reg_mins // 60)
            total_reg_m = int(total_period_reg_mins % 60)
            total_ot_h = int(total_period_ot_mins // 60)
            total_ot_m = int(total_period_ot_mins % 60)
            pdf.cell(col_widths[3], 8, f"{total_reg_h:02d}:{total_reg_m:02d}", 1, 0, 'C', fill=True) 
            pdf.cell(col_widths[4], 8, f"{total_ot_h:02d}:{total_ot_m:02d}", 1, 0, 'C', fill=True) 
            pdf.cell(col_widths[5], 8, f"C$ {total_period_pay:.2f}", 1, 0, 'R', fill=True) 
            pdf.ln(15)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Pago Total del Período: C$ {total_period_pay:.2f}", 0, 1)
            pdf.output(save_path, "F")
            logger.info(f"PDF guardado exitosamente en: {save_path}")
            QMessageBox.information(self, "Éxito", f"El reporte PDF para {employee_name} se ha guardado correctamente.")
        except Exception as e:
            logger.error(f"Error al generar el PDF: {e}")
            QMessageBox.critical(self, "Error de PDF", f"Ocurrió un error al generar el archivo PDF:\n{e}")

    def generate_random_attendance(self):
        start_date_q = self.payroll_start_date.date()
        end_date_q = self.payroll_end_date.date()
        start_date = start_date_q.toPyDate()
        end_date = end_date_q.toPyDate()
        if start_date > end_date:
            QMessageBox.warning(self, "Fechas Inválidas", "La fecha de inicio no puede ser posterior a la fecha de fin.")
            return
        logger.info(f"Preparando para generar datos aleatorios desde {start_date} hasta {end_date}...")
        confirm = QMessageBox.warning(self, "Confirmar Generación de Datos", "Esto añadirá registros de entrada/salida aleatorios a la base de datos para el período seleccionado.\n¿Está seguro de que desea continuar?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.No:
            logger.info("Operación cancelada.")
            return
        current_employees = self.app_controller.data_manager.get_employees()
        if not current_employees:
            QMessageBox.critical(self, "Error", "No se pudieron cargar los datos de empleados desde la BD.")
            return
        new_entries_batch = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                for employee in current_employees:
                    emp_id = employee.get("id_empleado")
                    if not emp_id: continue
                    if random.random() < 0.9: 
                        try:
                            entry_hour = 12
                            entry_minute = random.randint(-15, 15)
                            entry_time = datetime.datetime(current_date.year, current_date.month, current_date.day, entry_hour, 0, 0) + datetime.timedelta(minutes=entry_minute)
                            exit_hour = 22
                            exit_minute = random.randint(-15, 60)
                            exit_time = datetime.datetime(current_date.year, current_date.month, current_date.day, exit_hour, 0, 0) + datetime.timedelta(minutes=exit_minute)
                            if exit_time > entry_time:
                                new_entries_batch.append((emp_id, entry_time.isoformat(timespec='seconds'), "entrada"))
                                new_entries_batch.append((emp_id, exit_time.isoformat(timespec='seconds'), "salida"))
                        except ValueError: 
                            logger.error(f"Error generando fecha para {emp_id} en {current_date}")
            current_date += datetime.timedelta(days=1)
        if not new_entries_batch:
            logger.info("No se generaron nuevos eventos.")
            QMessageBox.information(self, "Éxito", "No se generaron nuevos datos (posiblemente solo eran fines de semana).")
            return
        success = self.app_controller.data_manager.add_attendance_events_batch(new_entries_batch)
        if success:
            logger.info(f"{len(new_entries_batch)} registros aleatorios añadidos a la BD")
            QMessageBox.information(self, "Éxito", f"Se generaron y añadieron {len(new_entries_batch)//2} días de trabajo aleatorios al historial.")
            self.calculate_payroll()
        else:
            logger.error(f"Error al guardar el historial de asistencia en la BD.")
            QMessageBox.critical(self, "Error", "No se pudo guardar el archivo de historial de asistencia.")

    def update_export_button_state(self):
        has_selection = bool(self.payroll_table.selectionModel().selectedRows())
        self.btn_export_pdf.setEnabled(has_selection)