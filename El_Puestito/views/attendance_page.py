import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QLineEdit, QHeaderView, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot
import requests
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
        print("[AttendancePage] Conectada a la señal 'lista_empleados_actualizada'.")


    def create_controls_bar(self):
        controls_layout = QHBoxLayout()
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Buscar empleado...")
        search_bar.setObjectName("search_bar")
        
        self.btn_limpiar = QPushButton("Limpiar Historial")
        self.btn_limpiar.setObjectName("orange_button") 
        self.btn_limpiar.setFixedWidth(200)
        
        controls_layout.addWidget(search_bar)
        controls_layout.addStretch()
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

    def load_and_refresh_table(self):
        print("Refrescando tabla de asistencia desde la BD...")
        self.employee_table.setRowCount(0)
        self.employee_row_map.clear()

        all_employees = self.app_controller.get_todos_los_empleados()
        
        today_events = self.app_controller.data_manager.get_events_for_today()

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
        employee_id = datos.get("employee_id")
        if not employee_id:
            return

        if employee_id not in self.employee_row_map:
            print(f"Se recibió asistencia para {employee_id} pero no está en la tabla. Refrescando todo.")
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
        
        print(f"✅ Tabla de Asistencia actualizada para ID {employee_id}. Nuevo estado: {new_status_text}")

    def limpiar_registros(self):
        texto_advertencia = ("¿Está seguro de que desea limpiar todos los registros?\n\n"
                            "Esto borrará PERMANENTEMENTE todo el historial de asistencia de la base de datos.\n\n"
                            "¡Esta acción no se puede deshacer!")
        
        confirm = QMessageBox.question(self, 
                                    "Confirmar Limpieza TOTAL", 
                                    texto_advertencia,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                    QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.No:
            return

        print("Limpiando TODO el historial de la base de datos...")
        
        self.app_controller.data_manager.clear_all_attendance_history()
        
        self.load_and_refresh_table()
        
        print("✅ Registros de historial limpiados. Tabla de asistencia reseteada.")
        QMessageBox.information(self,"Limpieza Completa", "Se ha borrado todo el historial de asistencia.")