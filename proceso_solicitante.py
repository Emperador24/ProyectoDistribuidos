import zmq
import json
import time
import sys
import multiprocessing
import os
import statistics
from datetime import datetime

class ProcesoSolicitante:
    def __init__(self, process_id, gestor_host="localhost", gestor_port=5555):
        self.gestor_host = gestor_host
        self.gestor_port = gestor_port
        self.process_id = process_id
        self.context = None
        self.socket = None

    def conectar(self):
        """Establece la conexión ZMQ dentro del proceso"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.gestor_host}:{self.gestor_port}")

    def enviar_peticion(self, peticion):
        """Envía una petición, mide el tiempo de respuesta y retorna la duración."""
        try:
            peticion_envio = peticion.copy()
            peticion_envio['timestamp'] = datetime.now().isoformat()
            mensaje = json.dumps(peticion_envio)
            
            # --- INICIO MEDICIÓN DE TIEMPO ---
            t_inicio = time.perf_counter()
            
            self.socket.send_string(mensaje)
            respuesta_str = self.socket.recv_string()
            
            t_fin = time.perf_counter()
            # --- FIN MEDICIÓN DE TIEMPO ---
            
            duracion = t_fin - t_inicio
            respuesta = json.loads(respuesta_str)
            
            # LOG DETALLADO
            estado_icon = "✓" if respuesta['estado'] == 'OK' else "✗"
            print(f"[Proc-{self.process_id}] {peticion['operacion']} | "
                  f"Tiempo: {duracion:.4f}s | {estado_icon} {respuesta['mensaje']}")
            
            return duracion
            
        except Exception as e:
            print(f"[Proc-{self.process_id} ERROR] {e}")
            return None

    def procesar_lista(self, lista_peticiones, tiempos_cola):
        """Procesa la lista de peticiones y guarda los tiempos en la cola compartida."""
        self.conectar()
        for peticion in lista_peticiones:
            duracion = self.enviar_peticion(peticion)
            if duracion is not None:
                tiempos_cola.put(duracion) # Guardar el tiempo en la cola compartida
        self.cerrar()

    def cerrar(self):
        """Cierra la conexión ZMQ (socket y contexto)."""
        if self.socket: 
            self.socket.close()
        if self.context: 
            self.context.term()

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

def proceso_trabajador(process_id, lista_completa, host, port, tiempos_cola):
    """Función wrapper para el proceso que recibe la cola para los tiempos."""
    cliente = ProcesoSolicitante(process_id, host, port)
    try:
        cliente.procesar_lista(lista_completa, tiempos_cola)
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
    
    todas_peticiones = leer_archivo_peticiones(archivo)
    if not todas_peticiones: return
    
    manager = multiprocessing.Manager()
    tiempos_cola = manager.Queue()

    print("=" * 70)
    print(f"[MAIN] INICIANDO PRUEBA DE RENDIMIENTO")
    print(f" - Peticiones por proceso: {len(todas_peticiones)}")
    print(f" - Procesos simultáneos:   {num_procesos}")
    print(f" - Total de llamadas:      {len(todas_peticiones) * num_procesos}")
    print("=" * 70)

    procesos = []
    start_time_global = time.perf_counter()

    for i in range(num_procesos):
        p = multiprocessing.Process(
            target=proceso_trabajador,
            args=(i, todas_peticiones, host, port, tiempos_cola)
        )
        procesos.append(p)
        p.start()
        
    for p in procesos:
        p.join()

    end_time_global = time.perf_counter()
    total_duration = end_time_global - start_time_global
    
    tiempos_completos = []
    while not tiempos_cola.empty():
        tiempos_completos.append(tiempos_cola.get())
        
    num_mediciones = len(tiempos_completos)

    print("\n" + "=" * 70)
    print("[MAIN] RESUMEN DE RENDIMIENTO")
    
    if num_mediciones > 0:
        average_time = statistics.mean(tiempos_completos)
        std_dev = statistics.stdev(tiempos_completos) if num_mediciones > 1 else 0

        requests_per_second = num_mediciones / total_duration
        requests_in_2_min = requests_per_second * 120

        print(f" Total de Mediciones Válidas: {num_mediciones}")
        print(f" Tiempo Total de Ejecución:   {total_duration:.4f} segundos")
        print("--- Métricas de Respuesta ---")
        print(f" ⏱️ Tiempo Promedio de Respuesta: {average_time:.4f} segundos")
        print(f" 📊 Desviación Estándar (Latencia): {std_dev:.4f} segundos")
        print("--- Proyección de Capacidad ---")
        print(f" 🚀 Rendimiento estimado: {requests_per_second:.2f} peticiones/segundo")
        print(f" 🎯 Capacidad estimada en 2 minutos: {int(requests_in_2_min):,} peticiones")
    else:
        print(" ⚠️ No se recibieron mediciones de tiempo válidas.")
        
    print("=" * 70)

if __name__ == "__main__":
    main()