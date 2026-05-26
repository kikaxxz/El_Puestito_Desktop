import firebase_admin
from firebase_admin import credentials, messaging
from logger_setup import setup_logger

logger = setup_logger()

class FirebaseService:
    def __init__(self, cred_path="firebase_credentials.json"):
        try:
            # Validamos que no se inicialice múltiples veces si el servidor hace un hot-reload
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {e}")

    def enviar_notificacion_tema(self, tema, titulo, cuerpo):
        """
        Envía una notificación push a todos los dispositivos suscritos a un tema.
        """
        try:
            mensaje = messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo,
                ),
                topic=tema, 
            )
            respuesta = messaging.send(mensaje)
            logger.info(f"Notificacion FCM enviada al tema '{tema}' con exito: {respuesta}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar notificacion FCM al tema: {e}")
            return False