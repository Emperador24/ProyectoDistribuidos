import zmq
import json
import time
import sys
import multiprocessing
import os
from datetime import datetime

class ProcesoSolicitante:
    def __init__(self, gestor_host="localhost", gestor_port=5555):
        """
        Inicializa el Proceso Solicitante.
        Nota: Ya no lee el archivo en el init para permitir flexibilidad en multiproceso.
        """
        self.gestor_host = gestor_host
        self.gestor_port = gestor_port
        self.context = None
        self.socket = None

    def conectar(self):
        """Establece la conexión ZMQ (Debe llamarse dentro del proceso específico)"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.gestor_host}:{self.gestor_port}")
        # Identificador visual para saber qué proceso escribe
        self.pid = os.getpid()
        print(f"[PS-{self.pid}] Conectado al Gestor de Carga en {self.gestor_host}:{self.gestor_port}")

    def enviar_peticion(self, peticion):
        """Envía una petición al Gestor de Carga y espera respuesta"""
        try:
            # Actualizar timestamp justo antes de enviar
            peticion['timestamp'] = datetime.now().isoformat()
            mensaje = json.dumps(peticion)
            print(f"[PS-{self.pid}] Enviando: {peticion['operacion']} - Libro: {peticion['codigo_libro']}")
            
            self.socket.send_string(mensaje)
            respuesta_str = self.socket.recv_string()
            respuesta = json.loads(respuesta_str)
            
            if respuesta['estado'] == 'OK':
                print(f"[PS-{self.pid}] ✓ R: {respuesta['mensaje']}")
            else:
                print(f"[PS-{self.pid}] ✗ R: {respuesta['mensaje']}")
            
            return respuesta
        except Exception as e:
            print(f"[PS-{self.pid} ERROR] {e}")
            return None

    def procesar_lista(self, lista_peticiones, delay=0):
        """Procesa una lista específica de peticiones"""
        self.conectar()
        
        exitosas = 0
        fallidas = 0
        
        for peticion in lista_peticiones:
            respuesta = self.enviar_peticion(peticion)
            if respuesta and respuesta['estado'] == 'OK':
                exitosas += 1
            else:
                fallidas += 1
            if delay > 0: 
                time.sleep(delay)

        self.cerrar()
        return exitosas, fallidas

    def cerrar(self):
        """Cierra la conexión"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()

# --- Funciones Estáticas de Ayuda ---

def leer_archivo_peticiones(archivo_path):
    """Lee el archivo y retorna una lista de diccionarios"""
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
        print(f"[MAIN] {len(peticiones)} peticiones cargadas desde {archivo_path}")
        return peticiones
    except FileNotFoundError:
        print(f"[MAIN ERROR] Archivo no encontrado: {archivo_path}")
        sys.exit(1)

def proceso_trabajador(sub_lista, host, port, delay):
    """
    Esta función corre dentro de cada subproceso.
    """
    # Cada proceso instancia su propio cliente para tener su propio socket
    cliente = ProcesoSolicitante(host, port)
    try:
        cliente.procesar_lista(sub_lista, delay)
    except KeyboardInterrupt:
        pass

def main():
    if len(sys.argv) < 2:
        print("Uso: python proceso_solicitante.py <archivo> [host] [port] [n_procesos]")
        print("Ejemplo: python proceso_solicitante.py peticiones.txt localhost 5555 4")
        sys.exit(1)
    
    archivo = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 5555
    
    # Nuevo parámetro: Número de procesos (default 1)
    num_procesos = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    
    # 1. Leer todas las peticiones en el proceso principal
    todas_peticiones = leer_archivo_peticiones(archivo)
    
    if not todas_peticiones:
        print("[MAIN] No hay peticiones para procesar.")
        return

    # 2. Dividir el trabajo (Chunking)
    # Si hay 10 peticiones y 2 procesos, cada uno recibe 5.
    # Usamos slicing con 'step' para distribuir tipo carta (round-robin)
    chunks = [todas_peticiones[i::num_procesos] for i in range(num_procesos)]
    
    # Eliminar chunks vacíos si hay más procesos que peticiones
    chunks = [c for c in chunks if len(c) > 0]
    
    print("=" * 60)
    print(f"[MAIN] Iniciando ejecución paralela")
    print(f" - Total peticiones: {len(todas_peticiones)}")
    print(f" - Procesos a lanzar: {len(chunks)}")
    print("=" * 60)

    procesos = []
    
    # 3. Crear y lanzar los subprocesos
    for i, sub_lista in enumerate(chunks):
        p = multiprocessing.Process(
            target=proceso_trabajador,
            args=(sub_lista, host, port, 0) # Delay 0 para máxima concurrencia
        )
        procesos.append(p)
        p.start()
        
    # 4. Esperar a que todos terminen
    for p in procesos:
        p.join()
        
    print("\n" + "=" * 60)
    print("[MAIN] Todos los procesos han finalizado.")
    print("=" * 60)

if __name__ == "__main__":
    main()