from PyQt6.QtCore import QThread

class ServerThread(QThread):
    def __init__(self, worker_instance, parent=None):
        super().__init__(parent)
        self.worker = worker_instance

    def run(self):
        if self.worker:
            self.worker.start_server()