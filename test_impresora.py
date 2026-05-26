import os
import sys
import ctypes
import usb.core
import usb.backend.libusb1
from escpos.printer import Usb

if os.name == 'nt' and sys.version_info >= (3, 8):
    os.add_dll_directory(os.getcwd())

dll_path = os.path.join(os.getcwd(), "libusb-1.0.dll")

try:
    ctypes.CDLL(dll_path)
    backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)
except Exception as e:
    print(e)
    sys.exit(1)

devices = list(usb.core.find(find_all=True, backend=backend))
impresoras = []

for dev in devices:
    try:
        es_impresora = False
        if dev.bDeviceClass == 7:
            es_impresora = True
        else:
            for cfg in dev:
                for intf in cfg:
                    if intf.bInterfaceClass == 7:
                        es_impresora = True
                        break
                if es_impresora:
                    break
        if es_impresora:
            impresoras.append((dev.idVendor, dev.idProduct))
    except Exception:
        pass

if not impresoras:
    print("Impresora no detectada")
    sys.exit(1)

for vid, pid in impresoras:
    try:
        printer = Usb(vid, pid, backend=backend)
        printer.set(align='center', bold=True)
        printer.text("EL PUESTITO\n")
        printer.text("TICKET DE PRUEBA\n")
        printer.text("-" * 32 + "\n")
        printer.set(align='left', normal_text=True)
        printer.text("1x Prueba de conexion        C$ 0.00\n")
        printer.text("-" * 32 + "\n")
        printer.text("STATUS: OK\n\n\n")
        printer.cut()
        print(f"Impresion exitosa en VID: {hex(vid)} PID: {hex(pid)}")
        break
    except Exception as e:
        print(f"Error en VID: {hex(vid)} PID: {hex(pid)} - {e}")