"""
Gestor de Carga (GC)
Recibe peticiones de PS y las distribuye según el tipo de operación
"""
import zmq
import json
from datetime import datetime, timedelta

class GestorCarga:
    def __init__(self, sede, ps_port=5555, pub_port=5556):
        """
        Inicializa el Gestor de Carga
        
        Args:
            sede: Identificador de la sede (1 o 2)
            ps_port: Puerto para recibir peticiones de PS
            pub_port: Puerto para publicar tópicos a Actores
        """
        self.sede = sede
        self.context = zmq.Context()
        
        # Socket REP para recibir peticiones de PS
        self.socket_ps = self.context.socket(zmq.REP)
        self.socket_ps.bind(f"tcp://*:{ps_port}")
        
        # Socket PUB para publicar tópicos a Actores
        self.socket_pub = self.context.socket(zmq.PUB)
        self.socket_pub.bind(f"tcp://*:{pub_port}")
        
        print(f"[GC-Sede{sede}] Iniciado en puertos PS:{ps_port}, PUB:{pub_port}")
        print(f"[GC-Sede{sede}] Esperando peticiones...")
    
    def procesar_devolucion(self, peticion):
        """
        Procesa una devolución de libro (asíncrona)
        Responde inmediatamente y publica el tópico DEVOLUCION
        """
        print(f"[GC-Sede{self.sede}] Procesando DEVOLUCIÓN - Libro: {peticion['codigo_libro']}")
        
        # Responder inmediatamente al PS
        respuesta = {
            'estado': 'OK',
            'mensaje': f'La biblioteca está recibiendo el libro {peticion["codigo_libro"]}',
            'operacion': 'DEVOLUCION',
            'timestamp': datetime.now().isoformat()
        }
        
        # Publicar tópico para los Actores
        topico = "DEVOLUCION"
        mensaje_actor = {
            'topico': topico,
            'codigo_libro': peticion['codigo_libro'],
            'usuario_id': peticion['usuario_id'],
            'sede': self.sede,
            'timestamp': peticion['timestamp']
        }
        
        mensaje_pub = f"{topico} {json.dumps(mensaje_actor)}"
        self.socket_pub.send_string(mensaje_pub)
        print(f"[GC-Sede{self.sede}] → Tópico publicado: {topico}")
        
        return respuesta
    
    def procesar_renovacion(self, peticion):
        """
        Procesa una renovación de libro (asíncrona)
        Responde inmediatamente con nueva fecha y publica el tópico RENOVACION
        """
        print(f"[GC-Sede{self.sede}] Procesando RENOVACIÓN - Libro: {peticion['codigo_libro']}")
        
        # Calcular nueva fecha de entrega (1 semana adicional)
        fecha_actual = datetime.now()
        nueva_fecha = fecha_actual + timedelta(weeks=1)
        
        # Responder inmediatamente al PS
        respuesta = {
            'estado': 'OK',
            'mensaje': f'Renovación exitosa. Nueva fecha de entrega: {nueva_fecha.strftime("%Y-%m-%d")}',
            'operacion': 'RENOVACION',
            'nueva_fecha_entrega': nueva_fecha.isoformat(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Publicar tópico para los Actores
        topico = "RENOVACION"
        mensaje_actor = {
            'topico': topico,
            'codigo_libro': peticion['codigo_libro'],
            'usuario_id': peticion['usuario_id'],
            'sede': self.sede,
            'fecha_actual': fecha_actual.isoformat(),
            'nueva_fecha_entrega': nueva_fecha.isoformat(),
            'timestamp': peticion['timestamp']
        }
        
        mensaje_pub = f"{topico} {json.dumps(mensaje_actor)}"
        self.socket_pub.send_string(mensaje_pub)
        print(f"[GC-Sede{self.sede}] → Tópico publicado: {topico}")
        
        return respuesta
    
    def procesar_prestamo(self, peticion):
        """
        Procesa un préstamo de libro (síncrona - para segunda entrega)
        Por ahora solo retorna respuesta básica
        """
        print(f"[GC-Sede{self.sede}] Procesando PRÉSTAMO - Libro: {peticion['codigo_libro']}")
        
        # Nota: En la primera entrega solo se implementan devolución y renovación
        # Esta funcionalidad se completará en la segunda entrega
        respuesta = {
            'estado': 'PENDIENTE',
            'mensaje': 'Funcionalidad de préstamo pendiente para segunda entrega',
            'operacion': 'PRESTAMO',
            'timestamp': datetime.now().isoformat()
        }
        
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
        contador = 0
        
        try:
            while True:
                # Esperar petición de PS
                peticion_str = self.socket_ps.recv_string()
                contador += 1
                
                print(f"\n{'='*60}")
                print(f"[GC-Sede{self.sede}] Petición #{contador} recibida")
                
                # Procesar petición
                respuesta = self.procesar_peticion(peticion_str)
                
                # Enviar respuesta al PS
                self.socket_ps.send_string(json.dumps(respuesta))
                print(f"[GC-Sede{self.sede}] ✓ Respuesta enviada")
                print(f"{'='*60}")
        
        except KeyboardInterrupt:
            print(f"\n[GC-Sede{self.sede}] Interrumpido por el usuario")
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cierra los sockets y el contexto"""
        self.socket_ps.close()
        self.socket_pub.close()
        self.context.term()
        print(f"[GC-Sede{self.sede}] Conexiones cerradas")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python gestor_carga.py <sede> [ps_port] [pub_port]")
        print("Ejemplo: python gestor_carga.py 1 5555 5556")
        sys.exit(1)
    
    sede = int(sys.argv[1])
    ps_port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555
    pub_port = int(sys.argv[3]) if len(sys.argv) > 3 else 5556
    
    gestor = GestorCarga(sede, ps_port, pub_port)
    gestor.ejecutar()


if __name__ == "__main__":
    main()