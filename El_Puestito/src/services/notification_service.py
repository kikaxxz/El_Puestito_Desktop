import sys
import os
import firebase_admin
from firebase_admin import credentials, messaging
from logger_setup import setup_logger

logger = setup_logger()

class NotificationService:
    def __init__(self, cred_filename="firebase_credentials.json"):
        self.cred_filename = cred_filename
        self._disabled = False
        self.inicializar()

    def inicializar(self):
        if self._disabled:
            return False
        try:
            if not firebase_admin._apps:
                # Detectar si estamos en el ejecutable de PyInstaller o en desarrollo puro
                if getattr(sys, 'frozen', False):
                    base_path = sys._MEIPASS
                else:
                    base_path = os.path.dirname(os.path.abspath(__file__))
                    
                cred_path = os.path.join(base_path, self.cred_filename)
                
                logger.info(f"Buscando credenciales de Firebase en: {cred_path}")
                
                # Validación estricta del archivo
                if not os.path.exists(cred_path):
                    logger.warning("Credenciales de Firebase ausentes. Servicio de notificaciones deshabilitado silenciosamente.")
                    self._disabled = True
                    return False
                    
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin inicializado correctamente.")
            return True
        except Exception as e:
            logger.error(f"Error CRITICO inicializando Firebase: {e}")
            return False

    def enviar_notificacion_tema(self, tema, titulo, cuerpo):
        if self._disabled:
            return False
            
        if not firebase_admin._apps:
            if not self.inicializar():
                return False

        try:
            mensaje = messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo,
                ),
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        default_vibrate_timings=True
                    )
                ),
                topic=tema, 
            )
            respuesta = messaging.send(mensaje)
            logger.info(f"Notificacion FCM enviada al tema '{tema}' con exito: {respuesta}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar notificacion FCM al tema: {e}")
            return False
notification_service = NotificationService()
