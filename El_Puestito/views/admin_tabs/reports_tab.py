from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCalendarWidget, QFrame, QTableWidget, QHeaderView, QTableWidgetItem
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from logger_setup import setup_logger

logger = setup_logger()

class ReportsTab(QWidget):
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.setup_ui()
        self.mostrar_reporte_del_dia()

    def setup_ui(self):
        reportes_layout = QVBoxLayout(self)
        reportes_layout.setContentsMargins(20, 20, 20, 20)
        reportes_layout.setSpacing(20)
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)
        cal_wrapper = QWidget()
        cal_layout = QVBoxLayout(cal_wrapper)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.setSpacing(5)
        lbl_fecha = QLabel("Seleccione fecha:")
        lbl_fecha.setStyleSheet("font-size: 16px; font-weight: bold; color: #dddddd;")
        cal_layout.addWidget(lbl_fecha)
        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("report_calendar")
        self.calendar.setGridVisible(True)
        self.calendar.setFixedSize(400, 280)
        cal_layout.addWidget(self.calendar)
        self.stats_card = QFrame()
        self.stats_card.setObjectName("stats_card")
        self.stats_card.setStyleSheet("""
            QFrame#stats_card {
                background-color: #2b2b2b; 
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
            QLabel { color: white; }
        """)
        stats_layout = QVBoxLayout(self.stats_card)
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.setSpacing(5)
        lbl_titulo_ventas = QLabel("VENTAS TOTALES DEL DÍA")
        lbl_titulo_ventas.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        lbl_titulo_ventas.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaaaaa; letter-spacing: 1px;") 
        stats_layout.addWidget(lbl_titulo_ventas)
        self.report_total_label = QLabel("C$ 0.00")
        self.report_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.report_total_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #4caf50;")
        stats_layout.addWidget(self.report_total_label)
        self.report_count_label = QLabel("0 artículos vendidos")
        self.report_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.report_count_label.setStyleSheet("font-size: 16px; color: #888888;")
        stats_layout.addWidget(self.report_count_label)
        top_layout.addWidget(cal_wrapper)
        top_layout.addWidget(self.stats_card)
        top_layout.setStretch(0, 0) 
        top_layout.setStretch(1, 1) 
        reportes_layout.addWidget(top_container)
        lbl_desglose = QLabel("Desglose de productos:")
        lbl_desglose.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        reportes_layout.addWidget(lbl_desglose)
        self.report_table = QTableWidget()
        self.report_table.setObjectName("employee_table") 
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Platillo", "Cantidad Vendida"])
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.report_table.setColumnWidth(1, 150)
        btn_web_report = QPushButton("Ver Gráficas Detalladas (Web)")
        btn_web_report.setObjectName("blue_button") 
        btn_web_report.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_web_report.setFixedHeight(40)
        btn_web_report.clicked.connect(self.abrir_reportes_web)
        reportes_layout.addWidget(btn_web_report) 
        reportes_layout.addWidget(self.report_table)
        self.calendar.selectionChanged.connect(self.mostrar_reporte_del_dia)

    def mostrar_reporte_del_dia(self):
        selected_date = self.calendar.selectedDate().toPyDate()
        selected_date_str = selected_date.isoformat()
        logger.info(f"Generando reporte visual para {selected_date_str}")
        total_ventas, items_vendidos = self.app_controller.data_manager.get_sales_report(selected_date_str)
        total_items = sum(item["cantidad_total"] for item in items_vendidos)
        self.report_total_label.setText(f"C$ {total_ventas:,.2f}") 
        self.report_count_label.setText(f"{total_items} artículos vendidos")
        self.report_table.setRowCount(len(items_vendidos))
        for row, item in enumerate(items_vendidos):
            item_nombre = QTableWidgetItem(item["nombre"])
            item_cantidad = QTableWidgetItem(str(item["cantidad_total"]))
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.report_table.setItem(row, 0, item_nombre)
            self.report_table.setItem(row, 1, item_cantidad)
        logger.info(f"Reporte generado. Total: C${total_ventas:.2f}")

    def abrir_reportes_web(self):
        selected_date = self.calendar.selectedDate().toPyDate().isoformat()
        url = f"{self.app_controller.SERVER_URL}/reportes-web?start={selected_date}&end={selected_date}"
        QDesktopServices.openUrl(QUrl(url))