import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QGroupBox, QFormLayout, QLineEdit, QTimeEdit, 
    QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QCalendarWidget, QListWidget
)
from PyQt6.QtCore import Qt, QTime, QDate
from PyQt6.QtGui import QTextCharFormat, QColor, QBrush
from logger_setup import setup_logger

logger = setup_logger()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SettingsTab(QWidget):
    def __init__(self, app_controller, config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.config = config
        self.setup_ui()
        try:
            self.load_settings()
        except Exception as e:
            logger.error(f"Error al cargar ajustes: {e}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)

        security_group = QGroupBox("Seguridad y Acceso (PINs)")
        sec_layout = QFormLayout()
        self.pins_inputs = {}
        for role in ["Administrador", "Cajero", "Cocinero", "Barra", "Ajustes_Sistema"]:
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setMaxLength(4)
            sec_layout.addRow(f"PIN {role}:", edit)
            self.pins_inputs[role] = edit
        security_group.setLayout(sec_layout)
        layout.addWidget(security_group)

        payroll_group = QGroupBox("Escala Salarial por Rol")
        pay_layout = QVBoxLayout()
        self.pay_table = QTableWidget(0, 3)
        self.pay_table.setHorizontalHeaderLabels(["Rol", "Pago Hora (C$)", "Pago Minuto (C$)"])
        self.pay_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pay_table.setFixedHeight(180)
        pay_layout.addWidget(self.pay_table)
        payroll_group.setLayout(pay_layout)
        layout.addWidget(payroll_group)

        horarios_group = QGroupBox("Control de Asistencia y Jornada")
        hor_layout = QFormLayout()
        self.entry_time = QTimeEdit()
        self.exit_time = QTimeEdit()
        self.entry_margin = QSpinBox()
        self.entry_margin.setSuffix(" min")
        self.exit_margin = QSpinBox()
        self.exit_margin.setSuffix(" min")
        
        hor_layout.addRow("Hora Entrada Oficial:", self.entry_time)
        hor_layout.addRow("Hora Salida Oficial:", self.exit_time)
        hor_layout.addRow("Margen Gracia Entrada:", self.entry_margin)
        hor_layout.addRow("Margen Gracia Salida:", self.exit_margin)
        horarios_group.setLayout(hor_layout)
        layout.addWidget(horarios_group)

        extras_group = QGroupBox("Políticas de Horas Extras y Feriados")
        ext_layout = QVBoxLayout()
        
        spinners_layout = QFormLayout()
        self.extra_mult = QDoubleSpinBox()
        self.extra_mult.setRange(1.0, 5.0)
        self.extra_mult.setSingleStep(0.5)
        self.holiday_mult = QDoubleSpinBox()
        self.holiday_mult.setRange(1.0, 5.0)
        self.holiday_mult.setSingleStep(0.5)
        spinners_layout.addRow("Multiplicador Hora Extra:", self.extra_mult)
        spinners_layout.addRow("Multiplicador Feriados:", self.holiday_mult)
        
        ext_layout.addLayout(spinners_layout)

        calendar_layout = QHBoxLayout()
        self.holiday_calendar = QCalendarWidget()
        self.holiday_calendar.setGridVisible(True)
        self.holiday_calendar.clicked.connect(self.add_holiday)
        self.holiday_calendar.currentPageChanged.connect(self.update_calendar_highlights)
        
        list_layout = QVBoxLayout()
        self.holidays_list = QListWidget()
        self.btn_remove_holiday = QPushButton("Eliminar Fecha Seleccionada")
        self.btn_remove_holiday.clicked.connect(self.remove_holiday)
        
        list_layout.addWidget(QLabel("Fechas Feriados (Día-Mes):"))
        list_layout.addWidget(self.holidays_list)
        list_layout.addWidget(self.btn_remove_holiday)
        
        calendar_layout.addWidget(self.holiday_calendar)
        calendar_layout.addLayout(list_layout)
        
        ext_layout.addLayout(calendar_layout)
        extras_group.setLayout(ext_layout)
        layout.addWidget(extras_group)

        self.btn_save = QPushButton("Guardar Todos los Ajustes")
        self.btn_save.setObjectName("orange_button")
        self.btn_save.setFixedHeight(40)
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def update_calendar_highlights(self):
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(QColor("#ff9500")))
        fmt.setForeground(QBrush(QColor("white")))

        self.holiday_calendar.setDateTextFormat(QDate(), QTextCharFormat())

        year = self.holiday_calendar.yearShown()
        for i in range(self.holidays_list.count()):
            date_str = self.holidays_list.item(i).text()
            try:
                day, month = map(int, date_str.split('-'))
                qdate = QDate(year, month, day)
                self.holiday_calendar.setDateTextFormat(qdate, fmt)
            except ValueError:
                continue

    def add_holiday(self, qdate):
        date_str = qdate.toString("dd-MM")
        existing_items = [self.holidays_list.item(i).text() for i in range(self.holidays_list.count())]
        if date_str not in existing_items:
            self.holidays_list.addItem(date_str)
            self.update_calendar_highlights()

    def remove_holiday(self):
        for item in self.holidays_list.selectedItems():
            self.holidays_list.takeItem(self.holidays_list.row(item))
        self.update_calendar_highlights()

    def load_settings(self):
        seguridad = self.config.get("seguridad", {})
        pins = seguridad.get("pines_acceso", seguridad.get("pines", {}))
        for role, edit in self.pins_inputs.items():
            edit.setText(pins.get(role, ""))

        roles = self.config.get("roles_pago", {})
        self.pay_table.setRowCount(len(roles))
        for i, (role, data) in enumerate(roles.items()):
            self.pay_table.setItem(i, 0, QTableWidgetItem(role))
            p_hora = data.get("pago_hora", data.get("hora", 0.0))
            p_min = data.get("pago_minuto", data.get("minuto", 0.0))
            self.pay_table.setItem(i, 1, QTableWidgetItem(str(p_hora)))
            self.pay_table.setItem(i, 2, QTableWidgetItem(str(p_min)))

        horarios = self.config.get("horarios_y_margenes", {})
        self.entry_time.setTime(QTime.fromString(horarios.get("entrada_oficial", "08:00"), "HH:mm"))
        self.exit_time.setTime(QTime.fromString(horarios.get("salida_oficial", "17:00"), "HH:mm"))
        self.entry_margin.setValue(horarios.get("margen_gracia_entrada", 0))
        self.exit_margin.setValue(horarios.get("margen_gracia_salida", 0))

        politicas = self.config.get("politicas_pago_extra", {})
        self.extra_mult.setValue(politicas.get("multiplicador_hora_extra", 2.0))
        feriados = politicas.get("feriados", {})
        self.holiday_mult.setValue(feriados.get("multiplicador", 2.0))
        
        self.holidays_list.clear()
        self.holidays_list.addItems(feriados.get("fechas", []))
        self.update_calendar_highlights()

    def save_settings(self):
        if "seguridad" not in self.config:
            self.config["seguridad"] = {}
        if "pines_acceso" not in self.config["seguridad"]:
            self.config["seguridad"]["pines_acceso"] = {}

        for role, edit in self.pins_inputs.items():
            self.config["seguridad"]["pines_acceso"][role] = edit.text()

        new_roles = {}
        for i in range(self.pay_table.rowCount()):
            role_item = self.pay_table.item(i, 0)
            hora_item = self.pay_table.item(i, 1)
            minuto_item = self.pay_table.item(i, 2)
            
            role = role_item.text() if role_item else f"Rol_{i}"
            
            try:
                pago_hora = float(hora_item.text()) if hora_item and hora_item.text() else 0.0
                pago_minuto = float(minuto_item.text()) if minuto_item and minuto_item.text() else 0.0
            except ValueError:
                pago_hora = 0.0
                pago_minuto = 0.0
                
            new_roles[role] = {
                "pago_hora": pago_hora,
                "pago_minuto": pago_minuto
            }
        self.config["roles_pago"] = new_roles

        self.config["horarios_y_margenes"] = {
            "entrada_oficial": self.entry_time.time().toString("HH:mm"),
            "salida_oficial": self.exit_time.time().toString("HH:mm"),
            "margen_gracia_entrada": self.entry_margin.value(),
            "margen_gracia_salida": self.exit_margin.value()
        }

        fechas = [self.holidays_list.item(i).text() for i in range(self.holidays_list.count())]
        self.config["politicas_pago_extra"] = {
            "multiplicador_hora_extra": self.extra_mult.value(),
            "feriados": {
                "multiplicador": self.holiday_mult.value(),
                "fechas": fechas
            }
        }

        if self.app_controller.save_config_to_file(self.config):
            QMessageBox.information(self, "Éxito", "Configuración actualizada correctamente.")
            if hasattr(self.app_controller, 'notify_server_config_change'):
                self.app_controller.notify_server_config_change()
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar el archivo de configuración.")