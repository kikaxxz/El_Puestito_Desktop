import logging
import datetime
from escpos.printer import Usb, Network, Dummy

logger = logging.getLogger(__name__)

class PrinterService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.printer = None

    def connect(self):
        config = self.config_manager.get_config()
        interface_type = config.get("printer_interface", "USB")
        
        try:
            if interface_type == "USB":
                vendor_id = int(config.get("usb_vendor_id", "0x04b8"), 16)
                product_id = int(config.get("usb_product_id", "0x0202"), 16)
                self.printer = Usb(vendor_id, product_id)
            elif interface_type == "WIFI":
                ip_address = config.get("printer_ip", "192.168.1.100")
                self.printer = Network(ip_address)
            elif interface_type == "DUMMY":
                self.printer = Dummy()
            return True
        except Exception as e:
            logger.error("Fallo al conectar con impresora: %s", str(e))
            self.printer = None
            return False

    def _align_line(self, left_str, right_str, total_length=32):
        spaces = total_length - len(left_str) - len(right_str)
        if spaces < 1:
            spaces = 1
        return f"{left_str}{' ' * spaces}{right_str}"

    def print_receipt(self, order_data, is_proforma=False):
        if not self.printer and not self.connect():
            return False
            
        config = self.config_manager.get_config()
        printer_settings = config.get("printer_settings", {})
        header_text = printer_settings.get("header", "EL PUESTITO\nTicket de Venta")
        footer_text = printer_settings.get("footer", "Gracias por su compra!")
            
        try:
            self.printer.set(align='center', bold=True)
            for line in header_text.split('\n'):
                if line.strip():
                    self.printer.text(line.strip()[:32].center(32) + "\n")
            
            self.printer.set(align='center', normal_text=True)
            self.printer.text("-" * 32 + "\n")
            
            if is_proforma:
                self.printer.text("PROFORMA / PRE-CUENTA".center(32) + "\n")
            else:
                self.printer.text("TICKET DE VENTA PAGADO".center(32) + "\n")
                
            self.printer.text("-" * 32 + "\n")
            
            # --- AGREGADO: FECHA Y HORA ---
            self.printer.set(align='left')
            now = datetime.datetime.now()
            date_str = now.strftime("%d/%m/%Y %H:%M")
            self.printer.text(self._align_line("Fecha:", date_str) + "\n")
            self.printer.text("-" * 32 + "\n")
            
            mesa_key = str(order_data.get('mesa_key', ''))
            if mesa_key:
                self.printer.set(align='left', bold=True)
                if '-' in mesa_key:
                    parts = mesa_key.split('-')
                    mesa_base = parts[0]
                    nombre_subcuenta = "-".join(parts[1:])
                    self.printer.text(f"Mesa: {mesa_base}\n")
                    self.printer.text(f"Sub-cuenta: {nombre_subcuenta}\n")
                elif '+' in mesa_key:
                    self.printer.text(f"Mesa(s): {mesa_key}\n")
                    self.printer.text("Cuenta Principal\n")
                else:
                    self.printer.text(f"Mesa: {mesa_key}\n")
                    self.printer.text("Cuenta Principal\n")
                
                self.printer.text("-" * 32 + "\n")
                self.printer.set(normal_text=True, bold=False)
            
            self.printer.set(align='left')
            total = float(order_data.get('total', 0))
            
            for item in order_data.get("items", []):
                qty = item.get('qty', item.get('cantidad', 1))
                
                name_base = item.get('name', item.get('nombre', ''))
                
                if item.get('nombre_cerveza'):
                    name_base = f"{name_base} ({item['nombre_cerveza']})"
                
                name = name_base[:20]
                
                price = float(item.get('price', item.get('precio_unitario', 0)))
                subtotal_item = qty * price
                
                left_part = f"{qty}x {name}"
                right_part = f"C$ {subtotal_item:.2f}"
                self.printer.text(self._align_line(left_part, right_part) + "\n")
            
            self.printer.text("-" * 32 + "\n")
            
            if is_proforma:
                self.printer.text(self._align_line("SUBTOTAL:", f"C$ {total:.2f}") + "\n")
                
                tips_active = []
                if printer_settings.get("tip1_enabled", True): 
                    tips_active.append(printer_settings.get("tip1_percent", 10))
                if printer_settings.get("tip2_enabled", True): 
                    tips_active.append(printer_settings.get("tip2_percent", 15))
                if printer_settings.get("tip3_enabled", False): 
                    tips_active.append(printer_settings.get("tip3_percent", 20))
                
                if tips_active:
                    self.printer.text("\n")
                
                for tip_percent in tips_active:
                    tip_amt = total * (tip_percent / 100.0)
                    total_with_tip = total + tip_amt
                    self.printer.text(self._align_line(f"PROPINA SUGERIDA ({tip_percent}%):", f"C$ {tip_amt:.2f}") + "\n")
                    self.printer.text(self._align_line(f"TOTAL CON {tip_percent}%:", f"C$ {total_with_tip:.2f}") + "\n")
                    self.printer.text("\n")
                    
                self.printer.text(self._align_line("TOTAL A PAGAR:", f"C$ {total:.2f}") + "\n")
            else:
                self.printer.text(self._align_line("TOTAL:", f"C$ {total:.2f}") + "\n")
            
            self.printer.set(align='center', normal_text=True)
            self.printer.text("-" * 32 + "\n")
            for line in footer_text.split('\n'):
                if line.strip():
                    self.printer.text(line.strip()[:32].center(32) + "\n")
            
            self.printer.cut()
            return True
        except Exception as e:
            logger.error("Fallo al imprimir ticket: %s", str(e))
            return False

    def open_cash_drawer(self):
        if not self.printer and not self.connect():
            return False
            
        try:
            self.printer.cashdraw(2)
            return True
        except Exception as e:
            logger.error("Fallo al abrir cajon: %s", str(e))
            return False