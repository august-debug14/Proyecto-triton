import argparse
import re

def parse_timeout(value: str) -> float:
    """
    Revisa que el tiempo de espera (timeout) sea un número decimal
    y que esté dentro del rango permitido (0.1 a 5.0 segundos).
    """
    try:
        val = float(value)
        
        if not (0.1 <= val <= 5.0):
            raise ValueError("El timeout debe estar entre 0.1 y 5.0 segundos.")
            
        return val
        
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Timeout inválido '{value}': {str(e)}")


def parse_cluster_id(value: str) -> str:
    """
    Verifica que el nombre del clúster tenga exactamente el formato que
    pide la empresa: cluster-<region>-<numero>.
    """
    pattern = r"^cluster-[a-z]{2,10}-[a-z]+-\d{2}$"
    
    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError(
            f"El ID del clúster '{value}' no tiene el formato correcto. "
        )
    return value