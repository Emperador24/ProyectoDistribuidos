"""
Proceso Solicitante (PS)
Genera y envía peticiones de operaciones de biblioteca al Gestor de Carga
"""
import zmq
import json
import time
import sys
from datetime import datetime

class ProcesoSolicitante:
    def __init__(self, archivo_peticiones, gestor_host="localhost", gestor_port=5555):
        """
        Inicializa el Proceso Solicitante
        
        Args:
            archivo_peticiones: Ruta al archivo con las peticiones
            gestor_host: Host del Gestor de Carga
            gestor_port: Puerto del Gestor de Carga
        """
        self.archivo_peticiones = archivo_peticiones
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{gestor_host}:{gestor_port}")
        print(f"[PS] Conectado al Gestor de Carga en {gestor_host}:{gestor_port}")
    
    def leer_peticiones(self):
        """
        Lee las peticiones desde el archivo de texto
        Formato esperado: OPERACION|CODIGO_LIBRO|USUARIO_ID
        """
        peticiones = []
        try:
            with open(self.archivo_peticiones, 'r', encoding='utf-8') as f:
                for linea in f:
                    linea = linea.strip()
                    if linea and not linea.startswith('#'):
                        partes = linea.split('|')
                        if len(partes) >= 3:
                            peticiones.append({
                                'operacion': partes[0].upper(),
                                'codigo_libro': partes[1],
                                'usuario_id': partes[2],
                                'timestamp': datetime.now().isoformat()
                            })
            print(f"[PS] {len(peticiones)} peticiones cargadas desde {self.archivo_peticiones}")
        except FileNotFoundError:
            print(f"[PS ERROR] Archivo no encontrado: {self.archivo_peticiones}")
            sys.exit(1)
        
        return peticiones
    
    def enviar_peticion(self, peticion):
        """
        Envía una petición al Gestor de Carga y espera respuesta
        """
        try:
            # Serializar petición
            mensaje = json.dumps(peticion)
            print(f"\n[PS] Enviando: {peticion['operacion']} - Libro: {peticion['codigo_libro']}")
            
            # Enviar petición
            self.socket.send_string(mensaje)
            
            # Esperar respuesta
            respuesta_str = self.socket.recv_string()
            respuesta = json.loads(respuesta_str)
            
            # Mostrar respuesta
            if respuesta['estado'] == 'OK':
                print(f"[PS] ✓ Respuesta: {respuesta['mensaje']}")
            else:
                print(f"[PS] ✗ Respuesta: {respuesta['mensaje']}")
            
            return respuesta
            
        except Exception as e:
            print(f"[PS ERROR] Error al enviar petición: {e}")
            return None
    
    def ejecutar(self, delay=0.5):
        """
        Ejecuta todas las peticiones con un delay entre cada una
        """
        peticiones = self.leer_peticiones()
        
        if not peticiones:
            print("[PS] No hay peticiones para procesar")
            return
        
        print(f"\n[PS] Iniciando procesamiento de {len(peticiones)} peticiones...")
        print("=" * 60)
        
        resultados = {
            'exitosas': 0,
            'fallidas': 0,
            'total': len(peticiones)
        }
        
        for i, peticion in enumerate(peticiones, 1):
            print(f"\n--- Petición {i}/{len(peticiones)} ---")
            respuesta = self.enviar_peticion(peticion)
            
            if respuesta and respuesta['estado'] == 'OK':
                resultados['exitosas'] += 1
            else:
                resultados['fallidas'] += 1
            
            # Pequeño delay entre peticiones
            if i < len(peticiones):
                time.sleep(delay)
        
        # Resumen final
        print("\n" + "=" * 60)
        print("[PS] RESUMEN DE EJECUCIÓN")
        print(f"Total de peticiones: {resultados['total']}")
        print(f"Exitosas: {resultados['exitosas']}")
        print(f"Fallidas: {resultados['fallidas']}")
        print("=" * 60)
    
    def cerrar(self):
        """Cierra la conexión con el Gestor de Carga"""
        self.socket.close()
        self.context.term()
        print("\n[PS] Conexión cerrada")


def main():
    if len(sys.argv) < 2:
        print("Uso: python proceso_solicitante.py <archivo_peticiones> [gestor_host] [gestor_port]")
        print("Ejemplo: python proceso_solicitante.py peticiones.txt localhost 5555")
        sys.exit(1)
    
    archivo = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 5555
    
    ps = ProcesoSolicitante(archivo, host, port)
    
    try:
        ps.ejecutar()
    except KeyboardInterrupt:
        print("\n[PS] Interrumpido por el usuario")
    finally:
        ps.cerrar()


if __name__ == "__main__":
    main()