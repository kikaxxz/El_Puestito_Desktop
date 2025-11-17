from PyQt6.QtCore import QThread

class ServerThread(QThread):
        def __init__(self, worker_instance, parent=None):
            super().__init__(parent)
            
            self.worker = worker_instance

        def run(self):
            """Este es el código que se ejecuta en el hilo separado."""
            print("[ServerThread] Hilo iniciado, llamando a worker.start_server()...")
            self.worker.start_server() 
            print("[ServerThread] worker.start_server() ha terminado. Hilo finalizando.")