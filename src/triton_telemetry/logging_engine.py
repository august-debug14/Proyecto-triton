import json
import logging
import logging.config
import logging.handlers
import queue
import os
import gzip
import shutil
from datetime import datetime, timezone


class AsyncJSONFormatter(logging.Formatter):
    """
    Esta clase se encarga de agarrar un mensaje de Log normal de Python
    y convertirlo en un formato JSON ordenado, ideal para que lo lean las máquinas.
    """
    
    def _serialize_exception(self, excepcion: BaseException) -> dict:
        """
        Función recursiva para buscar en los errores.
        Si hay un ExceptionGroup o errores encadenados, los extrae.
        """
        datos_error = {
            "tipo_error": excepcion.__class__.__name__,
            "mensaje": str(excepcion),
            "notas_forenses": getattr(excepcion, "__notes__", [])
        }

        if isinstance(excepcion, BaseExceptionGroup):
            datos_error["errores_agrupados"] = [
                self._serialize_exception(error_hijo)
                for error_hijo in excepcion.exceptions
            ]
            
        elif excepcion.__cause__:
            datos_error["causa_raiz"] = self._serialize_exception(excepcion.__cause__)
            
        return datos_error

    def format(self, record: logging.LogRecord) -> str:
        """
        Esta es la función principal que Python llama para darle formato al Log.
        """
        tiempo_utc = datetime.fromtimestamp(record.created, tz=timezone.utc)
        
        log_diccionario = {
            "fecha_hora": tiempo_utc.isoformat().replace("+00:00", "Z"),
            "nivel": record.levelname,
            "proceso_id": record.process,
            "hilo": record.threadName,
            "tarea_asincrona": getattr(record, "taskName", "Ninguna"),
            "mensaje": record.getMessage()
        }

        if record.exc_info:
            _, valor_excepcion, _ = record.exc_info
            if valor_excepcion:
                log_diccionario["arbol_de_errores"] = self._serialize_exception(valor_excepcion)

        campos_reservados_python = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "taskName"
        }
        
        for llave, valor in record.__dict__.items():
            if llave not in campos_reservados_python and not llave.startswith('_'):
                log_diccionario[llave] = valor

        return json.dumps(log_diccionario, ensure_ascii=False)

def gzip_namer(nombre_archivo: str) -> str:
    """
    Le dice al sistema cómo se debe llamar el archivo viejo al rotarlo.
    Simplemente le agregamos '.gz' al final.
    """
    return nombre_archivo + ".gz"

def gzip_rotator(origen: str, destino: str):
    """
    Esta función se activa justo cuando el archivo llega a 2MB.
    Agarra el archivo viejo, lo comprime en GZIP y borra el original plano.
    """
    with open(origen, 'rb') as archivo_entrada:
        with gzip.open(destino, 'wb', compresslevel=9) as archivo_salida:
            shutil.copyfileobj(archivo_entrada, archivo_salida)
            
    os.remove(origen)

def setup_triton_logging(log_filename: str = "triton_services.log") -> logging.Logger:
    """
    Configura todo el sistema de observabilidad.
    Unimos el formateador JSON con el sistema de colas y archivos rotativos.
    """
    esquema_logging = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "formato_json": {
                "()": "triton_telemetry.logging_engine.AsyncJSONFormatter"
            },
            "formato_consola": {
                "format": "%(asctime)s [%(levelname)s] (%(taskName)s) %(message)s",
                "datefmt": "%H:%M:%S"
            }
        },
        "handlers": {
            "consola": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "formato_consola",
                "stream": "ext://sys.stdout"
            },
            "archivo_rotativo": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "formato_json",
                "filename": log_filename,
                "maxBytes": 2 * 1024 * 1024,
                "backupCount": 3,            
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "triton_monitor": {
                "level": "DEBUG",
                "handlers": ["consola", "archivo_rotativo"],
                "propagate": False
            }
        }
    }

    logging.config.dictConfig(esquema_logging)
    logger_app = logging.getLogger("triton_monitor")

    for handler in logger_app.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.namer = gzip_namer
            handler.rotator = gzip_rotator

    cola_logs = queue.Queue(-1) 
    
    handler_cola = logging.handlers.QueueHandler(cola_logs)
    
    handlers_reales = logger_app.handlers
    
    listener = logging.handlers.QueueListener(cola_logs, *handlers_reales, respect_handler_level=True)
    
    logger_app.handlers = [handler_cola]
    
    listener.start()
    
    logger_app.listener = listener

    return logger_app