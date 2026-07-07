import os
import json
from PyQt6.QtCore import QObject, pyqtSignal
from src.path_manager import get_persistent_path
from logger_setup import setup_logger

logger = setup_logger()

class ConfigService(QObject):
    config_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._config = self._load_config()

    def get_config(self):
        return self._config

    def get(self, key, default=None):
        return self._config.get(key, default)

    def _load_config(self):
        try:
            config_path = get_persistent_path("config.json")
            if not os.path.exists(config_path):
                logger.warning(f"No se encontro {config_path}")
                return {}
                
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuracion en ConfigService: {e}")
            return {}

    def save_config(self, config_data):
        config_path = get_persistent_path("config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            self._config = config_data
            self.config_updated.emit(self._config)
            logger.info("Configuracion guardada en config.json")
            return True
        except Exception as e:
            logger.critical(f"Error guardando config.json: {e}")
            return False

    def deduplicate_pins(self):
        # Fase 5: Elimina claves alternativas como `pines` y `pines_acceso`.
        seguridad = self._config.get("seguridad", {})
        if "pines" in seguridad and "pines_acceso" in seguridad:
            del seguridad["pines"]
            self.save_config(self._config)

# Singleton instance
config_service = ConfigService()
