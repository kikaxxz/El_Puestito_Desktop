import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QGroupBox, QFormLayout, QLineEdit, QTimeEdit, 
    QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QCalendarWidget, QListWidget,
    QAbstractSpinBox, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QTime, QDate
from PyQt6.QtGui import QTextCharFormat, QColor, QBrush, QFont, QIntValidator, QDoubleValidator
from logger_setup import setup_logger

logger = setup_logger()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FloatDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QDoubleValidator(0.0, 9999.99, 2, editor)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        editor.setValidator(validator)
        return editor

class SettingsTab(QWidget):
    def __init__(self, app_controller, config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.config = config
        self.is_loading = True
        self.setup_ui()
        try:
            self.load_settings()
        except Exception as e:
            logger.error(f"Error al cargar ajustes: {e}")
        finally:
            self.is_loading = False

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        
        left_column = QVBoxLayout()
        left_column.setSpacing(20)
        
        right_column = QVBoxLayout()
        right_column.setSpacing(20)

        groupbox_style = """
            QGroupBox { color: white; font-weight: bold; border: 1px solid #444; border-radius: 6px; margin-top: 12px; padding-top: 15px;} 
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #ff9500; }
        """
        input_style = "padding: 6px; border-radius: 4px; background: #2b2b2b; color: white; border: 1px solid #555;"

        security_group = QGroupBox("Seguridad y Acceso (PINs)")
        security_group.setStyleSheet(groupbox_style)
        sec_layout = QFormLayout()
        sec_layout.setSpacing(12)
        
        self.pins_inputs = {}
        pin_validator = QIntValidator(0, 9999, self)
        
        for role in ["Administrador", "Cajero", "Cocinero", "Barra", "Ajustes_Sistema"]:
            pin_container = QHBoxLayout()
            pin_container.setSpacing(5)
            
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setMaxLength(4)
            edit.setValidator(pin_validator)
            edit.setStyleSheet(input_style)
            edit.setMaximumWidth(150)
            
            btn_eye = QPushButton("👁")
            btn_eye.setFixedWidth(30)
            btn_eye.setStyleSheet("background: #444; color: white; border-radius: 4px; padding: 5px;")
            btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_eye.clicked.connect(lambda checked, e=edit: self.toggle_pin_visibility(e))
            
            pin_container.addWidget(edit)
            pin_container.addWidget(btn_eye)
            pin_container.addStretch()
            
            sec_layout.addRow(QLabel(f"PIN {role}:"), pin_container)
            self.pins_inputs[role] = edit
            
        security_group.setLayout(sec_layout)
        left_column.addWidget(security_group)

        payroll_group = QGroupBox("Escala Salarial por Rol")
        payroll_group.setStyleSheet(groupbox_style)
        pay_layout = QVBoxLayout()
        
        self.pay_table = QTableWidget(0, 3)
        self.pay_table.setHorizontalHeaderLabels(["Rol", "Pago Hora (C$)", "Pago Minuto (C$)"])
        self.pay_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pay_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.pay_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.pay_table.setItemDelegateForColumn(1, FloatDelegate(self.pay_table))
        self.pay_table.setAlternatingRowColors(True)
        self.pay_table.setShowGrid(False)
        self.pay_table.setStyleSheet("""
            QTableWidget { background: #1e1e24; color: white; border-radius: 5px; border: 1px solid #444; }
            QHeaderView::section { background-color: #2b2b2b; color: white; padding: 5px; border: none; font-weight: bold; }
            QTableWidget::item { padding: 5px; }
        """)
        self.pay_table.cellChanged.connect(self.calculate_minute_pay)
        self.pay_table.setFixedHeight(200)
        
        pay_layout.addWidget(self.pay_table)
        
        btn_pay_actions = QHBoxLayout()
        self.btn_add_role = QPushButton("+ Añadir Rol")
        self.btn_add_role.setStyleSheet("background-color: #2e7d32; color: white; padding: 5px; border-radius: 4px; font-weight: bold;")
        self.btn_add_role.clicked.connect(self.add_new_role)
        
        self.btn_del_role = QPushButton("- Eliminar Rol")
        self.btn_del_role.setStyleSheet("background-color: #c62828; color: white; padding: 5px; border-radius: 4px; font-weight: bold;")
        self.btn_del_role.clicked.connect(self.remove_selected_role)
        
        btn_pay_actions.addWidget(self.btn_add_role)
        btn_pay_actions.addWidget(self.btn_del_role)
        pay_layout.addLayout(btn_pay_actions)
        
        pay_layout.addWidget(QLabel("<i>* El pago por minuto se calcula automáticamente.</i>"))
        payroll_group.setLayout(pay_layout)
        left_column.addWidget(payroll_group)

        horarios_group = QGroupBox("Control de Asistencia y Jornada")
        horarios_group.setStyleSheet(groupbox_style)
        hor_layout = QFormLayout()
        hor_layout.setSpacing(12)
        
        self.entry_time = QTimeEdit()
        self.exit_time = QTimeEdit()
        self.entry_margin = QSpinBox()
        self.entry_margin.setSuffix(" min")
        self.exit_margin = QSpinBox()
        self.exit_margin.setSuffix(" min")
        
        for widget in [self.entry_time, self.exit_time, self.entry_margin, self.exit_margin]:
            widget.setStyleSheet(input_style)
            widget.setMaximumWidth(150)
            widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        
        hor_layout.addRow("Hora Entrada Oficial:", self.entry_time)
        hor_layout.addRow("Hora Salida Oficial:", self.exit_time)
        hor_layout.addRow("Margen Gracia Entrada:", self.entry_margin)
        hor_layout.addRow("Margen Gracia Salida:", self.exit_margin)
        
        horarios_group.setLayout(hor_layout)
        right_column.addWidget(horarios_group)

        extras_group = QGroupBox("Políticas de Horas Extras y Feriados")
        extras_group.setStyleSheet(groupbox_style)
        ext_layout = QVBoxLayout()
        ext_layout.setSpacing(15)
        
        spinners_layout = QHBoxLayout()
        
        self.extra_mult = QDoubleSpinBox()
        self.extra_mult.setRange(1.0, 5.0)
        self.extra_mult.setSingleStep(0.5)
        self.extra_mult.setStyleSheet(input_style)
        
        self.holiday_mult = QDoubleSpinBox()
        self.holiday_mult.setRange(1.0, 5.0)
        self.holiday_mult.setSingleStep(0.5)
        self.holiday_mult.setStyleSheet(input_style)
        
        spinners_layout.addWidget(QLabel("Mult. Hora Extra:"))
        spinners_layout.addWidget(self.extra_mult)
        spinners_layout.addStretch()
        spinners_layout.addWidget(QLabel("Mult. Feriados:"))
        spinners_layout.addWidget(self.holiday_mult)
        
        ext_layout.addLayout(spinners_layout)

        calendar_layout = QHBoxLayout()
        self.holiday_calendar = QCalendarWidget()
        self.holiday_calendar.setGridVisible(True)
        self.holiday_calendar.setStyleSheet("""
            QCalendarWidget QWidget { alternate-background-color: #2b2b2b; }
            QCalendarWidget QAbstractItemView:enabled { background-color: #1e1e24; color: white; selection-background-color: #ff9500; }
            QCalendarWidget QToolButton { color: white; background-color: #2b2b2b; border-radius: 3px; }
        """)
        self.holiday_calendar.clicked.connect(self.add_holiday)
        self.holiday_calendar.currentPageChanged.connect(self.update_calendar_highlights)
        
        list_layout = QVBoxLayout()
        self.holidays_list = QListWidget()
        self.holidays_list.setStyleSheet("background: #2b2b2b; color: white; border-radius: 5px; border: 1px solid #444;")
        self.holidays_list.setMaximumWidth(150)
        
        self.btn_remove_holiday = QPushButton("Eliminar Fecha")
        self.btn_remove_holiday.setStyleSheet("background-color: #ff4c4c; color: white; padding: 5px; border-radius: 4px; font-weight: bold;")
        self.btn_remove_holiday.clicked.connect(self.remove_holiday)
        
        list_layout.addWidget(QLabel("Fechas Feriados:"))
        list_layout.addWidget(self.holidays_list)
        list_layout.addWidget(self.btn_remove_holiday)
        
        calendar_layout.addWidget(self.holiday_calendar)
        calendar_layout.addLayout(list_layout)
        
        ext_layout.addLayout(calendar_layout)
        extras_group.setLayout(ext_layout)
        right_column.addWidget(extras_group)

        columns_layout.addLayout(left_column, 1)
        columns_layout.addLayout(right_column, 1)
        container_layout.addLayout(columns_layout)

        self.btn_save = QPushButton("Guardar Todos los Ajustes")
        self.btn_save.setMinimumHeight(50)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #ff9500;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #e68a00;
            }
            QPushButton:pressed {
                background-color: #cc7a00;
            }
        """)
        self.btn_save.clicked.connect(self.save_settings)
        container_layout.addWidget(self.btn_save)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def toggle_pin_visibility(self, edit_widget):
        if edit_widget.echoMode() == QLineEdit.EchoMode.Password:
            edit_widget.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            edit_widget.setEchoMode(QLineEdit.EchoMode.Password)

    def add_new_role(self):
        row = self.pay_table.rowCount()
        self.pay_table.insertRow(row)
        
        item_role = QTableWidgetItem("Nuevo Rol")
        self.pay_table.setItem(row, 0, item_role)
        
        self.pay_table.setItem(row, 1, QTableWidgetItem("0.0"))
        
        item_min = QTableWidgetItem("0.0")
        item_min.setFlags(item_min.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.pay_table.setItem(row, 2, item_min)

    def remove_selected_role(self):
        current_row = self.pay_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selección", "Por favor selecciona un rol de la tabla para eliminarlo.")
            return
            
        role_name = self.pay_table.item(current_row, 0).text()
        confirm = QMessageBox.question(self, "Confirmar", f"¿Estás seguro de eliminar el rol '{role_name}'?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.pay_table.removeRow(current_row)

    def calculate_minute_pay(self, row, column):
        if not self.is_loading and column == 1:
            try:
                hora_item = self.pay_table.item(row, 1)
                pago_hora = float(hora_item.text())
                pago_minuto = round(pago_hora / 60, 4)
                
                minuto_item = self.pay_table.item(row, 2)
                if not minuto_item:
                    minuto_item = QTableWidgetItem()
                    minuto_item.setFlags(minuto_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.pay_table.setItem(row, 2, minuto_item)
                
                minuto_item.setText(str(pago_minuto))
            except ValueError:
                pass

    def update_calendar_highlights(self):
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(QColor("#ff9500")))
        fmt.setForeground(QBrush(QColor("white")))
        fmt.setFontWeight(QFont.Weight.Bold)

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
            
            min_item = QTableWidgetItem(str(p_min))
            min_item.setFlags(min_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pay_table.setItem(i, 2, min_item)

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
            
            if not role_item or not role_item.text().strip():
                continue
                
            role = role_item.text().strip()
            
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