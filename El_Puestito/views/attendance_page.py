import datetime
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QLineEdit, QHeaderView, QTableWidgetItem, QMessageBox, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSlot
from logger_setup import setup_logger

logger = setup_logger()

class AttendancePage(QWidget):

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        
        self.employee_row_map = {} 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 25)
        main_layout.setSpacing(20)
        
        controls_layout = self.create_controls_bar()
        table_title = QLabel("Lista de Empleados")
        table_title.setObjectName("section_title")
        
        self.employee_table = self.create_employee_table()
        
        main_layout.addLayout(controls_layout)
        self.btn_limpiar.clicked.connect(self.limpiar_registros)
        main_layout.addWidget(table_title)
        main_layout.addWidget(self.employee_table)
        
        self.load_and_refresh_table()
        self.app_controller.lista_empleados_actualizada.connect(self.load_and_refresh_table)
        self.app_controller.asistencia_recibida.connect(self.registrar_asistencia)
        logger.info("[AttendancePage] Conectada a la senal lista_empleados_actualizada.")

    def create_controls_bar(self):
        controls_layout = QHBoxLayout()
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Buscar empleado...")
        search_bar.setObjectName("search_bar")
        search_bar.textChanged.connect(self.filtrar_empleados)
        
        self.btn_export = QPushButton("Exportar CSV")
        self.btn_export.setObjectName("blue_button")
        self.btn_export.clicked.connect(self.exportar_csv)

        self.btn_limpiar = QPushButton("Limpiar Historial")
        self.btn_limpiar.setObjectName("orange_button") 
        self.btn_limpiar.setFixedWidth(200)
        
        controls_layout.addWidget(search_bar)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_export)
        controls_layout.addWidget(self.btn_limpiar) 
        return controls_layout

    def create_employee_table(self):
        table = QTableWidget()
        table.setObjectName("employee_table")
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Nombre", "Hora de Entrada", "Hora de Salida", "Estado"])
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)
        return table

    def filtrar_empleados(self, texto):
        for row in range(self.employee_table.rowCount()):
            item_nombre = self.employee_table.item(row, 0)
            if item_nombre:
                if texto.lower() in item_nombre.text().lower():
                    self.employee_table.setRowHidden(row, False)
                else:
                    self.employee_table.setRowHidden(row, True)

    def load_and_refresh_table(self):
        logger.info("Refrescando tabla de asistencia desde la BD...")
        try:
            self.employee_table.setRowCount(0)
            self.employee_row_map.clear()

            all_employees = self.app_controller.get_todos_los_empleados()
            from src.database.repositories.attendance import attendance_repo
            today_events = attendance_repo.get_events_for_today()

            employee_states = {}
            for event in today_events:
                emp_id = event['id_empleado']
                if emp_id not in employee_states:
                    employee_states[emp_id] = {"entrada": "-", "salida": "-", "estado": "Ausente"}

                event_time = datetime.datetime.fromisoformat(event['last_timestamp']).strftime("%I:%M %p")
                
                if event['tipo'] == 'entrada':
                    employee_states[emp_id]['entrada'] = event_time
                    employee_states[emp_id]['estado'] = "Presente"
                    employee_states[emp_id]['salida'] = "-" 
                elif event['tipo'] == 'salida':
                    employee_states[emp_id]['salida'] = event_time
                    employee_states[emp_id]['estado'] = "Ausente"

            self.employee_table.setRowCount(len(all_employees))
            for row, emp in enumerate(all_employees):
                emp_id = emp['id_empleado']
                state = employee_states.get(emp_id, {"entrada": "-", "salida": "-", "estado": "Ausente"})
                
                item_nombre = QTableWidgetItem(emp["nombre"])
                item_nombre.setData(Qt.ItemDataRole.UserRole, emp_id)
                
                self.employee_table.setItem(row, 0, item_nombre)
                self.employee_table.setItem(row, 1, QTableWidgetItem(state["entrada"]))
                self.employee_table.setItem(row, 2, QTableWidgetItem(state["salida"]))
                
                cell_widget = self.create_status_widget(state["estado"])
                self.employee_table.setCellWidget(row, 3, cell_widget)
                self.employee_row_map[emp_id] = row
                
        except Exception as e:
            logger.error(f"Error al cargar la tabla de asistencia: {e}")
            QMessageBox.critical(self, "Error de Datos", "No se pudo cargar la informacion de asistencia.")

    def create_status_widget(self, status_txt):
        cell_widget = QWidget()
        h_layout = QHBoxLayout(cell_widget)
        h_layout.setContentsMargins(8, 0, 0, 0)
        h_layout.setSpacing(10)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        dot = QLabel()
        dot.setObjectName("status_indicator")
        dot.setFixedSize(14, 14)
        dot.setProperty("status", "present" if status_txt.lower().startswith("pres") else "absent")
        text = QLabel(status_txt)
        text.setObjectName("status_text")
        h_layout.addWidget(dot)
        h_layout.addWidget(text)
        return cell_widget

    @pyqtSlot(dict)
    def registrar_asistencia(self, datos):
        try:
            employee_id = datos.get("employee_id")
            if not employee_id:
                return

            if employee_id not in self.employee_row_map:
                logger.warning(f"Se recibio asistencia para {employee_id} pero no esta en la tabla. Refrescando todo.")
                self.load_and_refresh_table()
                return
                
            fila = self.employee_row_map[employee_id]
            hora_actual = datetime.datetime.fromisoformat(datos['timestamp']).strftime("%I:%M %p")
            event_type = datos['event_type']
            
            new_status_text = ""
            new_status_property = ""
            
            if event_type == "entrada":
                self.employee_table.setItem(fila, 1, QTableWidgetItem(hora_actual))
                self.employee_table.setItem(fila, 2, QTableWidgetItem("-")) 
                new_status_text = "Presente"
                new_status_property = "present"
            else: 
                self.employee_table.setItem(fila, 2, QTableWidgetItem(hora_actual))
                new_status_text = "Ausente"
                new_status_property = "absent"

            widget_estado = self.employee_table.cellWidget(fila, 3)
            if widget_estado:
                dot = widget_estado.findChild(QLabel, "status_indicator")
                text = widget_estado.findChild(QLabel, "status_text")
                if dot:
                    dot.setProperty("status", new_status_property)
                    dot.style().polish(dot) 
                if text:
                    text.setText(new_status_text)
            
            logger.info(f"Tabla de Asistencia actualizada para ID {employee_id}. Nuevo estado: {new_status_text}")
        except Exception as e:
            logger.error(f"Error al registrar asistencia en la vista: {e}")

    def limpiar_registros(self):
        texto_advertencia = ("¿Esta seguro de que desea limpiar todos los registros?\n\n"
                            "Esto borrara PERMANENTEMENTE todo el historial de asistencia de la base de datos.\n\n"
                            "¡Esta accion no se puede deshacer!")
        
        confirm = QMessageBox.question(self, 
                                    "Confirmar Limpieza TOTAL", 
                                    texto_advertencia,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                    QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.No:
            return

        pin, ok = QInputDialog.getText(self, "PIN de Administrador", "Ingrese el PIN de administrador para continuar:", QLineEdit.EchoMode.Password)
        if not ok or not pin:
            return

        admin_pin_str = str(self.app_controller.config.get('seguridad', {}).get('pines_acceso', {}).get('Admin', '')).strip()
        
        if str(pin).strip() != admin_pin_str or not admin_pin_str:
            QMessageBox.critical(self, "Acceso Denegado", "PIN incorrecto. Operacion cancelada.")
            logger.warning("Intento fallido de limpiar registros de asistencia: PIN incorrecto.")
            return

        logger.info("Limpiando TODO el historial de la base de datos...")
        
        try:
            if confirm == QMessageBox.StandardButton.Yes:
                from src.database.repositories.attendance import attendance_repo
                attendance_repo.clear_all_attendance_history()
                self.load_and_refresh_table()
                logger.info("Registros de historial limpiados. Tabla de asistencia reseteada.")
                QMessageBox.information(self,"Limpieza Completa", "Se ha borrado todo el historial de asistencia.")
        except Exception as e:
            logger.error(f"Error al limpiar los registros de asistencia: {e}")
            QMessageBox.critical(self, "Error", "No se pudo limpiar el historial de asistencia.")

    def exportar_csv(self):
        try:
            if self.employee_table.rowCount() == 0:
                QMessageBox.warning(self, "Sin datos", "No hay datos en la tabla para exportar.")
                return

            fecha_hoy = datetime.date.today().isoformat()
            default_filename = f"asistencia_{fecha_hoy}.csv"
            save_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte CSV", default_filename, "CSV Files (*.csv)")

            if not save_path:
                return

            with open(save_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                headers = [self.employee_table.horizontalHeaderItem(i).text() for i in range(self.employee_table.columnCount())]
                writer.writerow(headers)

                for row in range(self.employee_table.rowCount()):
                    row_data = []
                    for col in range(self.employee_table.columnCount()):
                        if col == 3:
                            widget = self.employee_table.cellWidget(row, col)
                            text_label = widget.findChild(QLabel, "status_text") if widget else None
                            row_data.append(text_label.text() if text_label else "Desconocido")
                        else:
                            item = self.employee_table.item(row, col)
                            row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            logger.info(f"Reporte de asistencia exportado a: {save_path}")
            QMessageBox.information(self, "Exito", "El reporte CSV ha sido generado correctamente.")
        except Exception as e:
            logger.error(f"Error al generar el archivo CSV: {e}")
            QMessageBox.critical(self, "Error de Exportacion", "Ocurrio un problema al crear el archivo.")
