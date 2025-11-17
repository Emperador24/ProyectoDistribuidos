import zmq
import json
import time
import sys
import multiprocessing
import os
from datetime import datetime

class ProcesoSolicitante:
    def __init__(self, gestor_host="localhost", gestor_port=5555):
        self.gestor_host = gestor_host
        self.gestor_port = gestor_port
        self.context = None
        self.socket = None

    def conectar(self):
        """Establece la conexión ZMQ (Debe llamarse dentro del proceso específico)"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.gestor_host}:{self.gestor_port}")
        self.pid = os.getpid()
        print(f"[PS-{self.pid}] Conectado al Gestor")

    def enviar_peticion(self, peticion):
        try:
            # Actualizar timestamp al momento exacto del envío
            peticion_envio = peticion.copy()
            peticion_envio['timestamp'] = datetime.now().isoformat()
            
            mensaje = json.dumps(peticion_envio)
            # print(f"[PS-{self.pid}] Enviando: {peticion_envio['operacion']} {peticion_envio['codigo_libro']}")
            
            self.socket.send_string(mensaje)
            respuesta_str = self.socket.recv_string()
            respuesta = json.loads(respuesta_str)
            
            if respuesta['estado'] == 'OK':
                print(f"[PS-{self.pid}] ✓ OK")
            else:
                print(f"[PS-{self.pid}] ✗ Error: {respuesta['mensaje']}")
            
            return respuesta
        except Exception as e:
            print(f"[PS-{self.pid} ERROR] {e}")
            return None

    def procesar_lista(self, lista_peticiones, delay=0):
        self.conectar()
        exitosas = 0
        for peticion in lista_peticiones:
            respuesta = self.enviar_peticion(peticion)
            if respuesta and respuesta['estado'] == 'OK':
                exitosas += 1
            if delay > 0: time.sleep(delay)
        self.cerrar()

    def cerrar(self):
        if self.socket: self.socket.close()
        if self.context: self.context.term()

# --- Funciones Auxiliares ---

def leer_archivo_peticiones(archivo_path):
    peticiones = []
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#'):
                    partes = linea.split('|')
                    if len(partes) >= 3:
                        peticiones.append({
                            'operacion': partes[0].upper(),
                            'codigo_libro': partes[1],
                            'usuario_id': partes[2]
                        })
        return peticiones
    except FileNotFoundError:
        print(f"Archivo no encontrado: {archivo_path}")
        sys.exit(1)

def proceso_trabajador(lista_completa, host, port, delay):
    """Cada trabajador recibe la LISTA COMPLETA"""
    cliente = ProcesoSolicitante(host, port)
    try:
        cliente.procesar_lista(lista_completa, delay)
    except KeyboardInterrupt:
        pass

def main():
    if len(sys.argv) < 2:
        print("Uso: python ps.py <archivo> [host] [port] [n_procesos]")
        sys.exit(1)
    
    archivo = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 5555
    num_procesos = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    
    # 1. Cargar peticiones una sola vez
    todas_peticiones = leer_archivo_peticiones(archivo)
    
    if not todas_peticiones:
        return

    print("=" * 60)
    print(f"[MAIN] INICIANDO TEST DE CARGA PARALELO")
    print(f" - Peticiones en archivo: {len(todas_peticiones)}")
    print(f" - Procesos paralelos:    {num_procesos}")
    print(f" - Total peticiones a enviar: {len(todas_peticiones) * num_procesos}")
    print("=" * 60)

    procesos = []
    
    # 2. Lanzar N procesos, cada uno con la lista COMPLETA
    for i in range(num_procesos):
        # Pasamos 'todas_peticiones' completa a cada proceso
        p = multiprocessing.Process(
            target=proceso_trabajador,
            args=(todas_peticiones, host, port, 0)
        )
        procesos.append(p)
        p.start()
        
    for p in procesos:
        p.join()
        
    print("\n[MAIN] Fin de la ejecución.")

if __name__ == "__main__":
    main()