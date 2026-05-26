import os
import sys
import ctypes
import datetime
import usb.core
import usb.backend.libusb1
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QCheckBox, QPushButton, QMessageBox, 
    QGroupBox, QFormLayout, QTabWidget, QSpinBox, QComboBox, QLineEdit, QStackedWidget
)
from PyQt6.QtCore import Qt
from logger_setup import setup_logger

logger = setup_logger()

def _load_local_libusb():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    dll_path = os.path.join(base_path, "libusb-1.0.dll")
    
    if os.path.exists(dll_path):
        try:
            if os.name == 'nt' and sys.version_info >= (3, 8):
                os.add_dll_directory(base_path)
            ctypes.CDLL(dll_path)
            return usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)
        except Exception as e:
            logger.error(str(e))
    return None

class PrinterTab(QWidget):
    def __init__(self, app_controller, config, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.config = config
        self.custom_backend = _load_local_libusb()
        self.setup_ui()
        self.load_settings()
        self.update_preview()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        settings_group = QGroupBox("Configuracion de Impresion")
        settings_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #3d3d3d; border-radius: 8px; margin-top: 10px; padding: 15px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        
        settings_layout = QFormLayout()
        settings_layout.setSpacing(15)
        
        self.combo_interface = QComboBox()
        self.combo_interface.addItems(["USB", "WIFI", "DUMMY (Sin impresora)"])
        self.combo_interface.setStyleSheet("padding: 5px; background-color: #2b2b2b; color: white; border-radius: 4px;")
        self.combo_interface.currentTextChanged.connect(self.toggle_interface_settings)

        self.usb_widget = QWidget()
        usb_layout = QHBoxLayout(self.usb_widget)
        usb_layout.setContentsMargins(0, 0, 0, 0)
        
        self.combo_usb_printers = QComboBox()
        self.combo_usb_printers.setStyleSheet("padding: 5px; background-color: #2b2b2b; color: white; border-radius: 4px;")
        self.combo_usb_printers.setMinimumWidth(200)
        
        self.btn_scan = QPushButton("Escanear")
        self.btn_scan.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px;")
        self.btn_scan.clicked.connect(self.scan_usb_printers)
        
        usb_layout.addWidget(self.combo_usb_printers, 1)
        usb_layout.addWidget(self.btn_scan)

        self.wifi_widget = QWidget()
        wifi_layout = QHBoxLayout(self.wifi_widget)
        wifi_layout.setContentsMargins(0, 0, 0, 0)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Ej. 192.168.1.100")
        self.ip_input.setStyleSheet("padding: 5px; background-color: #2b2b2b; color: white; border-radius: 4px;")
        wifi_layout.addWidget(self.ip_input)

        self.interface_stack = QStackedWidget()
        self.interface_stack.addWidget(self.usb_widget)
        self.interface_stack.addWidget(self.wifi_widget)
        self.interface_stack.addWidget(QWidget())

        lbl_interface = QLabel("Tipo de Conexión:")
        lbl_interface.setStyleSheet("font-weight: bold;")
        lbl_device = QLabel("Dispositivo/IP:")
        lbl_device.setStyleSheet("font-weight: bold;")

        settings_layout.addRow(lbl_interface, self.combo_interface)
        settings_layout.addRow(lbl_device, self.interface_stack)
        
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #555;")
        settings_layout.addRow(line)

        self.header_input = QTextEdit()
        self.header_input.setFixedHeight(70)
        self.header_input.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555; border-radius: 5px; padding: 5px;")
        self.header_input.textChanged.connect(self.update_preview)
        
        self.footer_input = QTextEdit()
        self.footer_input.setFixedHeight(70)
        self.footer_input.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555; border-radius: 5px; padding: 5px;")
        self.footer_input.textChanged.connect(self.update_preview)
        
        self.chk_proforma = QCheckBox("Habilitar impresion de Proforma (Pre-cuenta)")
        self.chk_proforma.setStyleSheet("font-size: 13px;")
        self.chk_proforma.stateChanged.connect(self.update_preview)

        lbl_header = QLabel("Encabezado del Ticket:")
        lbl_header.setStyleSheet("font-weight: bold;")
        lbl_footer = QLabel("Pie de pagina:")
        lbl_footer.setStyleSheet("font-weight: bold;")

        settings_layout.addRow(lbl_header, self.header_input)
        settings_layout.addRow(lbl_footer, self.footer_input)
        settings_layout.addRow("", self.chk_proforma)
        
        self.chk_tip1 = QCheckBox("Sugerencia Propina 1")
        self.spin_tip1 = QSpinBox()
        self.spin_tip1.setRange(0, 100)
        self.spin_tip1.setSuffix("%")
        self.spin_tip1.setFixedWidth(70)
        self.chk_tip1.stateChanged.connect(self.update_preview)
        self.spin_tip1.valueChanged.connect(self.update_preview)
        
        self.chk_tip2 = QCheckBox("Sugerencia Propina 2")
        self.spin_tip2 = QSpinBox()
        self.spin_tip2.setRange(0, 100)
        self.spin_tip2.setSuffix("%")
        self.spin_tip2.setFixedWidth(70)
        self.chk_tip2.stateChanged.connect(self.update_preview)
        self.spin_tip2.valueChanged.connect(self.update_preview)

        self.chk_tip3 = QCheckBox("Sugerencia Propina 3")
        self.spin_tip3 = QSpinBox()
        self.spin_tip3.setRange(0, 100)
        self.spin_tip3.setSuffix("%")
        self.spin_tip3.setFixedWidth(70)
        self.chk_tip3.stateChanged.connect(self.update_preview)
        self.spin_tip3.valueChanged.connect(self.update_preview)

        tip1_layout = QHBoxLayout()
        tip1_layout.addWidget(self.chk_tip1)
        tip1_layout.addWidget(self.spin_tip1)
        tip1_layout.addStretch()

        tip2_layout = QHBoxLayout()
        tip2_layout.addWidget(self.chk_tip2)
        tip2_layout.addWidget(self.spin_tip2)
        tip2_layout.addStretch()

        tip3_layout = QHBoxLayout()
        tip3_layout.addWidget(self.chk_tip3)
        tip3_layout.addWidget(self.spin_tip3)
        tip3_layout.addStretch()

        lbl_propinas = QLabel("Opciones de Propina:")
        lbl_propinas.setStyleSheet("font-weight: bold;")

        settings_layout.addRow(lbl_propinas, tip1_layout)
        settings_layout.addRow("", tip2_layout)
        settings_layout.addRow("", tip3_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Configuracion")
        self.btn_save.setFixedHeight(45)
        self.btn_save.setStyleSheet("QPushButton { background-color: #f76606; color: white; font-weight: bold; font-size: 14px; border-radius: 8px; } QPushButton:hover { background-color: #ff7b24; } QPushButton:pressed { background-color: #d65500; }")
        self.btn_save.clicked.connect(self.save_settings)

        self.btn_test = QPushButton("Imprimir Prueba")
        self.btn_test.setFixedHeight(45)
        self.btn_test.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px; border-radius: 8px; } QPushButton:hover { background-color: #45a049; }")
        self.btn_test.clicked.connect(self.print_test_ticket)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_test)
        
        layout_v_settings = QVBoxLayout()
        layout_v_settings.addLayout(settings_layout)
        layout_v_settings.addStretch()
        layout_v_settings.addLayout(btn_layout)
        settings_group.setLayout(layout_v_settings)
        
        preview_group = QGroupBox("Visor de Tickets")
        preview_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #3d3d3d; border-radius: 8px; margin-top: 10px; padding: 15px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_tabs = QTabWidget()
        self.preview_tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #3d3d3d; border-radius: 5px; background-color: #1e1e24; } QTabBar::tab { background: #2b2b2b; color: #aaa; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; } QTabBar::tab:selected { background: #3d3d3d; color: white; font-weight: bold; }")
        
        proforma_tab = QWidget()
        proforma_layout = QVBoxLayout(proforma_tab)
        proforma_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_proforma = QTextEdit()
        self.preview_proforma.setReadOnly(True)
        self.preview_proforma.setFixedSize(320, 450)
        self.preview_proforma.setStyleSheet("background-color: #ffffff; color: #000000; font-family: 'Courier New', Courier, monospace; font-size: 13px; padding: 15px; border: none; border-radius: 0px;")
        proforma_layout.addWidget(self.preview_proforma)
        
        final_tab = QWidget()
        final_layout = QVBoxLayout(final_tab)
        final_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_final = QTextEdit()
        self.preview_final.setReadOnly(True)
        self.preview_final.setFixedSize(320, 450)
        self.preview_final.setStyleSheet("background-color: #ffffff; color: #000000; font-family: 'Courier New', Courier, monospace; font-size: 13px; padding: 15px; border: none; border-radius: 0px;")
        final_layout.addWidget(self.preview_final)
        
        self.preview_tabs.addTab(proforma_tab, "Proforma (Pre-cuenta)")
        self.preview_tabs.addTab(final_tab, "Ticket Final (Pagado)")
        
        preview_layout.addWidget(self.preview_tabs)
        
        main_layout.addWidget(settings_group, 45)
        main_layout.addWidget(preview_group, 55)

    def toggle_interface_settings(self, interface_type):
        if interface_type == "USB":
            self.interface_stack.setCurrentIndex(0)
        elif interface_type == "WIFI":
            self.interface_stack.setCurrentIndex(1)
        else:
            self.interface_stack.setCurrentIndex(2)

    def scan_usb_printers(self):
        self.combo_usb_printers.clear()
        self.btn_scan.setText("Buscando...")
        self.btn_scan.setEnabled(False)
        
        try:
            devices = list(usb.core.find(find_all=True, backend=self.custom_backend))
            found_count = 0
            
            for dev in devices:
                es_impresora = False
                if dev.bDeviceClass == 7:
                    es_impresora = True
                else:
                    try:
                        for cfg in dev:
                            for intf in cfg:
                                if intf.bInterfaceClass == 7:
                                    es_impresora = True
                                    break
                            if es_impresora: break
                    except: pass
                
                if es_impresora:
                    vid_hex = hex(dev.idVendor)
                    pid_hex = hex(dev.idProduct)
                    self.combo_usb_printers.addItem(f"Impresora USB (VID:{vid_hex} PID:{pid_hex})", (vid_hex, pid_hex))
                    found_count += 1
                    
            if found_count == 0:
                self.combo_usb_printers.addItem("Ninguna impresora detectada", None)
        except Exception as e:
            logger.error(str(e))
            self.combo_usb_printers.addItem("Error al escanear puertos", None)
            
        self.btn_scan.setText("Escanear")
        self.btn_scan.setEnabled(True)

    def load_settings(self):
        printer_conf = self.config.get("printer_settings", {})
        
        interface = printer_conf.get("printer_interface", "USB")
        self.combo_interface.setCurrentText(interface)
        
        vid = printer_conf.get("usb_vendor_id", "0x04b8")
        pid = printer_conf.get("usb_product_id", "0x0202")
        self.combo_usb_printers.addItem(f"Impresora Guardada (VID:{vid} PID:{pid})", (vid, pid))
        
        self.ip_input.setText(printer_conf.get("printer_ip", "192.168.1.100"))
        
        self.header_input.setText(printer_conf.get("header", "EL PUESTITO\nTicket de Venta"))
        self.footer_input.setText(printer_conf.get("footer", "Gracias por su compra!"))
        self.chk_proforma.setChecked(printer_conf.get("enable_proforma", True))
        
        self.chk_tip1.setChecked(printer_conf.get("tip1_enabled", True))
        self.spin_tip1.setValue(printer_conf.get("tip1_percent", 10))
        
        self.chk_tip2.setChecked(printer_conf.get("tip2_enabled", True))
        self.spin_tip2.setValue(printer_conf.get("tip2_percent", 15))
        
        self.chk_tip3.setChecked(printer_conf.get("tip3_enabled", False))
        self.spin_tip3.setValue(printer_conf.get("tip3_percent", 20))

    def _align_line(self, left_str, right_str, total_length=32):
        spaces = total_length - len(left_str) - len(right_str)
        if spaces < 1:
            spaces = 1
        return f"{left_str}{' ' * spaces}{right_str}"

    def _format_receipt(self, header, footer, is_proforma):
        lines = []
        
        for h_line in header.split('\n'):
            if h_line.strip():
                lines.append(h_line.strip()[:32].center(32))
                
        lines.append("-" * 32)
        
        if is_proforma:
            lines.append("PROFORMA / PRE-CUENTA".center(32))
        else:
            lines.append("TICKET DE VENTA PAGADO".center(32))
            
        lines.append("-" * 32)
        
        now = datetime.datetime.now()
        date_str = now.strftime("%d/%m/%Y %H:%M")
        lines.append(self._align_line("Fecha:", date_str))
        lines.append("-" * 32)
        
        lines.append(self._align_line("1x Hamb. Sencilla", "C$ 150.00"))
        lines.append(self._align_line("1x Michelada (Corona)", "C$ 190.00"))
        lines.append("-" * 32)
        
        subtotal = 340.00
        
        if is_proforma:
            lines.append(self._align_line("SUBTOTAL:", f"C$ {subtotal:.2f}"))
            
            tips_active = []
            if self.chk_tip1.isChecked(): tips_active.append(self.spin_tip1.value())
            if self.chk_tip2.isChecked(): tips_active.append(self.spin_tip2.value())
            if self.chk_tip3.isChecked(): tips_active.append(self.spin_tip3.value())
            
            if tips_active:
                lines.append("")
            
            for tip_percent in tips_active:
                tip_amt = subtotal * (tip_percent / 100.0)
                total_with_tip = subtotal + tip_amt
                lines.append(self._align_line(f"PROPINA SUGERIDA ({tip_percent}%):", f"C$ {tip_amt:.2f}"))
                lines.append(self._align_line(f"TOTAL CON {tip_percent}%:", f"C$ {total_with_tip:.2f}"))
                lines.append("")
                
            lines.append(self._align_line("TOTAL A PAGAR:", f"C$ {subtotal:.2f}"))
        else:
            lines.append(self._align_line("TOTAL:", f"C$ {subtotal:.2f}"))
            
        lines.append("-" * 32)
        
        for f_line in footer.split('\n'):
            if f_line.strip():
                lines.append(f_line.strip()[:32].center(32))
                
        return "\n".join(lines)

    def update_preview(self):
        header = self.header_input.toPlainText()
        footer = self.footer_input.toPlainText()
        
        proforma_text = self._format_receipt(header, footer, is_proforma=True)
        self.preview_proforma.setPlainText(proforma_text)

        final_text = self._format_receipt(header, footer, is_proforma=False)
        self.preview_final.setPlainText(final_text)

    def save_settings(self):
        if "printer_settings" not in self.config:
            self.config["printer_settings"] = {}
            
        interface = self.combo_interface.currentText().split()[0]
        self.config["printer_settings"]["printer_interface"] = interface
        
        if interface == "USB":
            data = self.combo_usb_printers.currentData()
            if data:
                self.config["printer_settings"]["usb_vendor_id"] = data[0]
                self.config["printer_settings"]["usb_product_id"] = data[1]
                
        elif interface == "WIFI":
            self.config["printer_settings"]["printer_ip"] = self.ip_input.text()
            
        self.config["printer_settings"]["header"] = self.header_input.toPlainText()
        self.config["printer_settings"]["footer"] = self.footer_input.toPlainText()
        self.config["printer_settings"]["enable_proforma"] = self.chk_proforma.isChecked()
        
        self.config["printer_settings"]["tip1_enabled"] = self.chk_tip1.isChecked()
        self.config["printer_settings"]["tip1_percent"] = self.spin_tip1.value()
        
        self.config["printer_settings"]["tip2_enabled"] = self.chk_tip2.isChecked()
        self.config["printer_settings"]["tip2_percent"] = self.spin_tip2.value()
        
        self.config["printer_settings"]["tip3_enabled"] = self.chk_tip3.isChecked()
        self.config["printer_settings"]["tip3_percent"] = self.spin_tip3.value()
        
        self.app_controller.save_config_to_file(self.config)
        QMessageBox.information(self, "Exito", "Configuracion de impresora guardada correctamente.")

    def print_test_ticket(self):
        self.save_settings()
        
        test_order = {
            "mesa_key": "Prueba",
            "total": 340.00,
            "items": [
                {"nombre": "Hamb. Sencilla", "cantidad": 1, "precio_unitario": 150.0},
                {"nombre": "Michelada", "nombre_cerveza": "Corona", "cantidad": 1, "precio_unitario": 190.0}
            ]
        }
        
        success = self.app_controller.printer_service.print_receipt(test_order, is_proforma=False)
        
        if success:
            QMessageBox.information(self, "Exito", "El ticket de prueba se envió correctamente a la impresora.")
        else:
            QMessageBox.warning(self, "Error", "No se pudo imprimir el ticket. Verifica la conexión física y los IDs seleccionados.")