import unittest
import os
import gzip
import json
import subprocess

class TestSimulacionCaos(unittest.TestCase):
    
    def test_inyeccion_caos_y_telemetria_json(self):
        """
        Forzamos un error en la consola y verificamos que el log guarde todo bien.
        """
        print("\n--- Iniciando Simulación de Caos (Test) ---")
        
        comando = [ 
            "python", "src/app_operator.py", 
            "AWS", "GCP", 
            "-c", "cluster-us-east-01", 
            "-t", "0.1", 
            "--chaos"
        ]
        
        subprocess.run(comando, capture_output=True, text=True)
        
        archivo_plano = "triton_services.log"
        archivo_comprimido = "triton_services.log.gz"
        
        log_encontrado = os.path.exists(archivo_plano) or os.path.exists(archivo_comprimido)
        
        self.assertTrue(log_encontrado, "El sistema de telemetría no generó ningún archivo de log.")
        
        if os.path.exists(archivo_plano):
            with open(archivo_plano, 'r') as f:
                lineas = f.readlines()
                
            self.assertTrue(len(lineas) > 0, "El archivo de log está vacío.")
            
            ultimo_log = json.loads(lineas[-1])
            
            self.assertIn("fecha_hora", ultimo_log)
            self.assertIn("hilo", ultimo_log)
            print("Metadatos forenses validados correctamente.")

if __name__ == '__main__':
    unittest.main()