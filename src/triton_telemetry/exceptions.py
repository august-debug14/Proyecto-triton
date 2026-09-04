class TritonError(Exception):
    """
    Excepción principal para todos los errores de nuestro proyecto Triton.
    """
    pass

class ProviderTimeoutError(TritonError):
    """
    Se lanza cuando un proveedor de nube tarda demasiado en responder.
    """
    pass

class CorruptedPayloadError(TritonError):
    """
    Se lanza cuando la respuesta del código HTTP indica un error.
    """
    pass

class NetworkPeeringError(TritonError):
    """
    Se lanza cuando hay un problema en el DNS.
    """
    pass