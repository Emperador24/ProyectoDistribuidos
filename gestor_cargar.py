"""
Gestor de Carga (GC)
Recibe peticiones de PS y las distribuye a los Actores usando REQ/REP:
- DEVOLUCION: Síncrona (REQ/REP con Actor de Devolución)
- RENOVACION: Síncrona (REQ/REP con Actor de Renovación)
- PRESTAMO: Síncrona (REQ/REP con Actor de Préstamo)
"""
import zmq
import json
from datetime import datetime, timedelta
import sys

class GestorCarga:
    def __init__(self, sede, ps_port=5555, 
                 actor_dev_port=5556, actor_ren_port=5557, actor_prest_port=5559):
        """
        Inicializa el Gestor de Carga
        
        Args:
            sede: Identificador de la sede (1 o 2)
            ps_port: Puerto para recibir peticiones de PS (REP)
            actor_dev_port: Puerto del Actor de Devolución (REQ)
            actor_ren_port: Puerto del Actor de Renovación (REQ)
            actor_prest_port: Puerto del Actor de Préstamo (REQ)
        """
        self.sede = sede
        self.context = zmq.Context()
        
        # Socket REP para recibir peticiones de PS
        self.socket_ps = self.context.socket(zmq.REP)
        self.socket_ps.bind(f"tcp://*:{ps_port}")
        
        # Socket REQ para Actor de Devolución (síncrono)
        self.socket_devolucion = self.context.socket(zmq.REQ)
        self.socket_devolucion.connect(f"tcp://localhost:{actor_dev_port}")
        
        # Socket REQ para Actor de Renovación (síncrono)
        self.socket_renovacion = self.context.socket(zmq.REQ)
        self.socket_renovacion.connect(f"tcp://localhost:{actor_ren_port}")
        
        # Socket REQ para Actor de Préstamo (síncrono)
        self.socket_prestamo = self.context.socket(zmq.REQ)
        self.socket_prestamo.connect(f"tcp://localhost:{actor_prest_port}")
        
        print(f"[GC-Sede{sede}] Iniciado (MODO SÍNCRONO):")
        print(f"  → Puerto PS (REP): {ps_port}")
        print(f"  → Actor Devolución (REQ): localhost:{actor_dev_port}")
        print(f"  → Actor Renovación (REQ): localhost:{actor_ren_port}")
        print(f"  → Actor Préstamo (REQ): localhost:{actor_prest_port}")
        print(f"[GC-Sede{sede}] Esperando peticiones...")
        
        self.contador_peticiones = 0
    
    def procesar_devolucion(self, peticion):
        """
        Procesa una devolución de libro (síncrona)
        Envía solicitud al Actor y espera respuesta
        """
        print(f"[GC-Sede{self.sede}] Procesando DEVOLUCIÓN - Libro: {peticion['codigo_libro']}")
        print(f"[GC-Sede{self.sede}] → Esperando respuesta del Actor de Devolución...")
        
        # Enviar solicitud al Actor de Devolución (bloqueante)
        mensaje_actor = {
            'codigo_libro': peticion['codigo_libro'],
            'usuario_id': peticion['usuario_id'],
            'timestamp': peticion['timestamp']
        }
        
        self.socket_devolucion.send_string(json.dumps(mensaje_actor))
        
        # Esperar respuesta del Actor (operación síncrona)
        respuesta_str = self.socket_devolucion.recv_string()
        respuesta_actor = json.loads(respuesta_str)
        
        # Preparar respuesta para PS
        if respuesta_actor['estado'] == 'OK':
            respuesta = {
                'estado': 'OK',
                'mensaje': f'Devolución procesada. {respuesta_actor.get("mensaje", "")}',
                'operacion': 'DEVOLUCION',
                'libro': respuesta_actor.get('libro', ''),
                'ejemplares_disponibles': respuesta_actor.get('ejemplares_disponibles', 0),
                'timestamp': datetime.now().isoformat()
            }
            print(f"[GC-Sede{self.sede}] ✓ Devolución procesada exitosamente")
        else:
            respuesta = {
                'estado': respuesta_actor['estado'],
                'mensaje': respuesta_actor['mensaje'],
                'operacion': 'DEVOLUCION',
                'timestamp': datetime.now().isoformat()
            }
            print(f"[GC-Sede{self.sede}] ✗ Error en devolución: {respuesta_actor['mensaje']}")
        
        return respuesta
    
    def procesar_renovacion(self, peticion):
        """
        Procesa una renovación de libro (síncrona)
        Envía solicitud al Actor y espera respuesta
        """
        print(f"[GC-Sede{self.sede}] Procesando RENOVACIÓN - Libro: {peticion['codigo_libro']}")
        print(f"[GC-Sede{self.sede}] → Esperando respuesta del Actor de Renovación...")
        
        # Calcular nueva fecha de entrega (1 semana adicional)
        fecha_actual = datetime.now()
        nueva_fecha = fecha_actual + timedelta(weeks=1)
        
        # Enviar solicitud al Actor de Renovación (bloqueante)
        mensaje_actor = {
            'codigo_libro': peticion['codigo_libro'],
            'usuario_id': peticion['usuario_id'],
            'nueva_fecha_entrega': nueva_fecha.isoformat(),
            'timestamp': peticion['timestamp']
        }
        
        self.socket_renovacion.send_string(json.dumps(mensaje_actor))
        
        # Esperar respuesta del Actor (operación síncrona)
        respuesta_str = self.socket_renovacion.recv_string()
        respuesta_actor = json.loads(respuesta_str)
        
        # Preparar respuesta para PS
        if respuesta_actor['estado'] == 'OK':
            respuesta = {
                'estado': 'OK',
                'mensaje': f'Renovación exitosa. Nueva fecha de entrega: {nueva_fecha.strftime("%Y-%m-%d")}',
                'operacion': 'RENOVACION',
                'nueva_fecha_entrega': nueva_fecha.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            print(f"[GC-Sede{self.sede}] ✓ Renovación procesada exitosamente")
        else:
            respuesta = {
                'estado': respuesta_actor['estado'],
                'mensaje': respuesta_actor['mensaje'],
                'operacion': 'RENOVACION',
                'timestamp': datetime.now().isoformat()
            }
            print(f"[GC-Sede{self.sede}] ✗ Error en renovación: {respuesta_actor['mensaje']}")
        
        return respuesta
    
    def procesar_prestamo(self, peticion):
        """
        Procesa un préstamo de libro (síncrona)
        Envía solicitud al Actor de Préstamo y espera respuesta
        """
        print(f"[GC-Sede{self.sede}] Procesando PRÉSTAMO - Libro: {peticion['codigo_libro']}")
        print(f"[GC-Sede{self.sede}] → Esperando respuesta del Actor de Préstamo...")
        
        # Enviar solicitud al Actor de Préstamo (bloqueante)
        mensaje_actor = {
            'codigo_libro': peticion['codigo_libro'],
            'usuario_id': peticion['usuario_id'],
            'timestamp': peticion['timestamp']
        }
        
        self.socket_prestamo.send_string(json.dumps(mensaje_actor))
        
        # Esperar respuesta del Actor (operación síncrona)
        respuesta_str = self.socket_prestamo.recv_string()
        respuesta_actor = json.loads(respuesta_str)
        
        # Preparar respuesta para PS
        if respuesta_actor['estado'] == 'OK':
            respuesta = {
                'estado': 'OK',
                'mensaje': f'Préstamo otorgado. Fecha de entrega: {respuesta_actor["fecha_entrega"]}',
                'operacion': 'PRESTAMO',
                'fecha_prestamo': respuesta_actor['fecha_prestamo'],
                'fecha_entrega': respuesta_actor['fecha_entrega'],
                'nombre_libro': respuesta_actor.get('nombre_libro', ''),
                'timestamp': datetime.now().isoformat()
            }
            print(f"[GC-Sede{self.sede}] ✓ Préstamo otorgado exitosamente")
        else:
            respuesta = {
                'estado': respuesta_actor['estado'],
                'mensaje': respuesta_actor['mensaje'],
                'operacion': 'PRESTAMO',
                'timestamp': datetime.now().isoformat()
            }
            print(f"[GC-Sede{self.sede}] ✗ Préstamo rechazado: {respuesta_actor['mensaje']}")
        
        return respuesta
    
    def procesar_peticion(self, peticion_str):
        """
        Procesa una petición recibida del PS
        """
        try:
            peticion = json.loads(peticion_str)
            operacion = peticion.get('operacion', '').upper()
            
            if operacion == 'DEVOLUCION':
                return self.procesar_devolucion(peticion)
            elif operacion == 'RENOVACION':
                return self.procesar_renovacion(peticion)
            elif operacion == 'PRESTAMO':
                return self.procesar_prestamo(peticion)
            else:
                return {
                    'estado': 'ERROR',
                    'mensaje': f'Operación desconocida: {operacion}',
                    'timestamp': datetime.now().isoformat()
                }
        
        except json.JSONDecodeError:
            return {
                'estado': 'ERROR',
                'mensaje': 'Formato de petición inválido',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'estado': 'ERROR',
                'mensaje': f'Error al procesar petición: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def ejecutar(self):
        """
        Ejecuta el loop principal del Gestor de Carga
        """
        print(f"\n[GC-Sede{self.sede}] ¡Listo para recibir peticiones!\n")
        
        try:
            while True:
                # Esperar petición de PS
                peticion_str = self.socket_ps.recv_string()
                self.contador_peticiones += 1
                
                print(f"\n{'='*70}")
                print(f"[GC-Sede{self.sede}] Petición #{self.contador_peticiones} recibida")
                
                # Procesar petición
                respuesta = self.procesar_peticion(peticion_str)
                
                # Enviar respuesta al PS
                self.socket_ps.send_string(json.dumps(respuesta))
                print(f"[GC-Sede{self.sede}] ✓ Respuesta enviada al PS")
                print(f"{'='*70}")
        
        except KeyboardInterrupt:
            print(f"\n[GC-Sede{self.sede}] Interrumpido por el usuario")
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cierra los sockets y el contexto"""
        self.socket_ps.close()
        self.socket_devolucion.close()
        self.socket_renovacion.close()
        self.socket_prestamo.close()
        self.context.term()
        
        print(f"\n{'='*70}")
        print(f"[GC-Sede{self.sede}] Estadísticas:")
        print(f"  Total peticiones procesadas: {self.contador_peticiones}")
        print(f"[GC-Sede{self.sede}] Conexiones cerradas")
        print(f"{'='*70}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python gestor_carga.py <sede> [ps_port] [actor_dev_port] [actor_ren_port] [actor_prest_port]")
        print("\nEjemplos:")
        print("  # Sede 1 - puertos: PS=5555, Dev=5556, Ren=5557, Prest=5559")
        print("  python gestor_carga.py 1 5555 5556 5557 5559")
        print("\n  # Sede 2 - puertos: PS=5565, Dev=5566, Ren=5567, Prest=5569")
        print("  python gestor_carga.py 2 5565 5566 5567 5569")
        sys.exit(1)
    
    sede = int(sys.argv[1])
    ps_port = int(sys.argv[2]) if len(sys.argv) > 2 else (5555 if sede == 1 else 5565)
    actor_dev_port = int(sys.argv[3]) if len(sys.argv) > 3 else (5556 if sede == 1 else 5566)
    actor_ren_port = int(sys.argv[4]) if len(sys.argv) > 4 else (5557 if sede == 1 else 5567)
    actor_prest_port = int(sys.argv[5]) if len(sys.argv) > 5 else (5559 if sede == 1 else 5569)
    
    gestor = GestorCarga(sede, ps_port, actor_dev_port, actor_ren_port, actor_prest_port)
    gestor.ejecutar()


if __name__ == "__main__":
    main()