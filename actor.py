"""
Actor Unificado
Procesa DEVOLUCION, RENOVACION (asíncronas) y PRESTAMO (síncrona)
Se comunica con el Gestor de Almacenamiento (GA) en lugar de la BD directamente
"""
import zmq
import json
from datetime import datetime, timedelta
import time
import sys

class Actor:
    def __init__(self, tipo, sede, gc_host="localhost", gc_port=5556, 
                 ga_host="localhost", ga_port=5560, puerto_rep=None):
        """
        Inicializa el Actor
        
        Args:
            tipo: Tipo de actor ('DEVOLUCION', 'RENOVACION' o 'PRESTAMO')
            sede: Identificador de la sede
            gc_host: Host del Gestor de Carga
            gc_port: Puerto del publisher del GC (para SUB) o puerto propio (para REP)
            ga_host: Host del Gestor de Almacenamiento
            ga_port: Puerto del Gestor de Almacenamiento
            puerto_rep: Puerto REP si es actor de préstamo (ej: 5559)
        """
        self.tipo = tipo.upper()
        self.sede = sede
        self.ga_host = ga_host
        self.ga_port = ga_port
        
        # Configurar ZeroMQ
        self.context = zmq.Context()
        
        # Socket para operaciones del actor (SUB o REP)
        if self.tipo == 'PRESTAMO':
            # PRÉSTAMO: Socket REP (síncrono)
            if puerto_rep is None:
                puerto_rep = 5559 if sede == 1 else 5560
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{puerto_rep}")
            print(f"[Actor-{self.tipo}-Sede{sede}] Iniciado en puerto {puerto_rep} (REP - Síncrono)")
        else:
            # DEVOLUCIÓN/RENOVACIÓN: Socket SUB (asíncrono)
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(f"tcp://{gc_host}:{gc_port}")
            self.socket.setsockopt_string(zmq.SUBSCRIBE, self.tipo)
            print(f"[Actor-{self.tipo}-Sede{sede}] Conectado a GC: {gc_host}:{gc_port} (SUB)")
            print(f"[Actor-{self.tipo}-Sede{sede}] Suscrito al tópico: {self.tipo}")
        
        # Socket REQ para comunicarse con el Gestor de Almacenamiento
        self.socket_ga = self.context.socket(zmq.REQ)
        self.socket_ga.connect(f"tcp://{ga_host}:{ga_port}")
        print(f"[Actor-{self.tipo}-Sede{sede}] Conectado a GA: {ga_host}:{ga_port}")
        
        self.contador_operaciones = 0
        self.operaciones_exitosas = 0
        self.operaciones_fallidas = 0
    
    def solicitar_ga(self, operacion, **parametros):
        """
        Envía una solicitud al Gestor de Almacenamiento y espera respuesta
        
        Args:
            operacion: Tipo de operación para el GA
            **parametros: Parámetros adicionales de la operación
            
        Returns:
            dict: Respuesta del GA
        """
        solicitud = {
            'operacion': operacion,
            **parametros
        }
        
        # Enviar solicitud
        self.socket_ga.send_string(json.dumps(solicitud))
        
        # Esperar respuesta
        respuesta_str = self.socket_ga.recv_string()
        respuesta = json.loads(respuesta_str)
        
        return respuesta
    
    def procesar_devolucion(self, mensaje):
        """
        Procesa una devolución de libro solicitando al GA
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        timestamp = mensaje['timestamp']
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando devolución:")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        
        # Solicitar UPDATE al GA
        print(f"[Actor-{self.tipo}-Sede{self.sede}] → Solicitando UPDATE a GA...")
        respuesta_update = self.solicitar_ga(
            'UPDATE_DEVOLUCION',
            codigo_libro=codigo_libro,
            usuario_id=usuario_id
        )
        
        if respuesta_update['estado'] != 'OK':
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en UPDATE: {respuesta_update['mensaje']}")
            self.operaciones_fallidas += 1
            return
        
        print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ BD actualizada:")
        print(f"  → Libro: {respuesta_update.get('libro', 'Desconocido')}")
        print(f"  → Ejemplares disponibles: {respuesta_update.get('ejemplares_disponibles', 0)}")
        
        # Solicitar INSERT historial al GA
        print(f"[Actor-{self.tipo}-Sede{self.sede}] → Registrando en historial...")
        respuesta_historial = self.solicitar_ga(
            'INSERT_HISTORIAL',
            codigo_libro=codigo_libro,
            usuario_id=usuario_id,
            tipo_operacion='DEVOLUCION',
            datos_adicionales=None
        )
        
        if respuesta_historial['estado'] == 'OK':
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Operación registrada en historial")
            print(f"[Actor-{self.tipo}-Sede{self.sede}] → Replicación asíncrona a BD secundaria iniciada")
            self.operaciones_exitosas += 1
        else:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ⚠ No se pudo registrar en historial")
            self.operaciones_fallidas += 1
    
    def procesar_renovacion(self, mensaje):
        """
        Procesa una renovación de libro solicitando al GA
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        nueva_fecha = mensaje['nueva_fecha_entrega']
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando renovación:")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        print(f"  → Nueva fecha: {nueva_fecha}")
        
        # Solicitar UPDATE al GA
        print(f"[Actor-{self.tipo}-Sede{self.sede}] → Solicitando UPDATE a GA...")
        respuesta_update = self.solicitar_ga(
            'UPDATE_RENOVACION',
            codigo_libro=codigo_libro,
            usuario_id=usuario_id,
            nueva_fecha=nueva_fecha
        )
        
        if respuesta_update['estado'] != 'OK':
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en UPDATE: {respuesta_update['mensaje']}")
            self.operaciones_fallidas += 1
            return
        
        print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Renovación registrada en BD")
        
        # Solicitar INSERT historial al GA
        print(f"[Actor-{self.tipo}-Sede{self.sede}] → Registrando en historial...")
        datos_adicionales = json.dumps({'nueva_fecha_entrega': nueva_fecha})
        respuesta_historial = self.solicitar_ga(
            'INSERT_HISTORIAL',
            codigo_libro=codigo_libro,
            usuario_id=usuario_id,
            tipo_operacion='RENOVACION',
            datos_adicionales=datos_adicionales
        )
        
        if respuesta_historial['estado'] == 'OK':
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Operación registrada en historial")
            print(f"[Actor-{self.tipo}-Sede{self.sede}] → Replicación asíncrona a BD secundaria iniciada")
            self.operaciones_exitosas += 1
        else:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ⚠ No se pudo registrar en historial")
            self.operaciones_fallidas += 1
    
    def procesar_prestamo(self, mensaje):
        """
        Procesa una solicitud de préstamo con transacción ACID (SÍNCRONO)
        
        Returns:
            dict: Respuesta con estado del préstamo
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        timestamp = mensaje.get('timestamp', datetime.now().isoformat())
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando solicitud de PRÉSTAMO (SÍNCRONO):")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        
        # PASO 1: Verificar disponibilidad
        print(f"[Actor-{self.tipo}-Sede{self.sede}] → Solicitando SELECT disponibilidad a GA...")
        respuesta_select = self.solicitar_ga(
            'SELECT_DISPONIBILIDAD',
            codigo_libro=codigo_libro
        )
        
        if respuesta_select['estado'] != 'OK':
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Libro no encontrado")
            self.operaciones_fallidas += 1
            return {
                'estado': 'RECHAZADO',
                'mensaje': 'Libro no encontrado en la biblioteca',
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
        
        disponibles = respuesta_select['ejemplares_disponibles']
        totales = respuesta_select['ejemplares_totales']
        nombre = respuesta_select['nombre']
        
        if disponibles <= 0:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Sin ejemplares disponibles (0/{totales})")
            self.operaciones_fallidas += 1
            return {
                'estado': 'RECHAZADO',
                'mensaje': f'No hay ejemplares disponibles. Total: {totales}, Disponibles: 0',
                'codigo_libro': codigo_libro,
                'nombre_libro': nombre,
                'timestamp': datetime.now().isoformat()
            }
        
        print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Libro disponible: {nombre}")
        print(f"[Actor-{self.tipo}-Sede{self.sede}]   Ejemplares: {disponibles}/{totales}")
        
        # PASO 2: Calcular fechas
        fecha_prestamo = datetime.now()
        fecha_entrega = fecha_prestamo + timedelta(weeks=2)
        
        # PASO 3: Solicitar transacción ACID al GA
        print(f"[Actor-{self.tipo}-Sede{self.sede}] → Solicitando TRANSACCION_PRESTAMO a GA...")
        respuesta_transaccion = self.solicitar_ga(
            'TRANSACCION_PRESTAMO',
            codigo_libro=codigo_libro,
            usuario_id=usuario_id,
            fecha_prestamo=fecha_prestamo.isoformat(),
            fecha_entrega=fecha_entrega.isoformat()
        )
        
        if respuesta_transaccion['estado'] != 'OK':
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en transacción: {respuesta_transaccion['mensaje']}")
            self.operaciones_fallidas += 1
            return {
                'estado': 'ERROR',
                'mensaje': respuesta_transaccion['mensaje'],
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
        
        print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Préstamo exitoso")
        print(f"[Actor-{self.tipo}-Sede{self.sede}]   Fecha entrega: {fecha_entrega.strftime('%Y-%m-%d')}")
        
        self.operaciones_exitosas += 1
        
        return {
            'estado': 'OK',
            'mensaje': f'Préstamo otorgado exitosamente',
            'codigo_libro': codigo_libro,
            'nombre_libro': nombre,
            'fecha_prestamo': fecha_prestamo.strftime('%Y-%m-%d'),
            'fecha_entrega': fecha_entrega.strftime('%Y-%m-%d'),
            'prestamo_id': respuesta_transaccion.get('prestamo_id'),
            'timestamp': datetime.now().isoformat()
        }
    
    def ejecutar(self):
        """
        Ejecuta el loop principal del Actor
        Comportamiento diferente según el tipo (SUB o REP)
        """
        if self.tipo == 'PRESTAMO':
            self.ejecutar_sincrono()
        else:
            self.ejecutar_asincrono()
    
    def ejecutar_asincrono(self):
        """
        Loop para actores asíncronos (DEVOLUCIÓN y RENOVACIÓN)
        """
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] ¡Esperando mensajes del tópico {self.tipo}!\n")
        
        try:
            while True:
                # Esperar mensaje del tópico
                mensaje_completo = self.socket.recv_string()
                
                # Separar tópico y contenido
                partes = mensaje_completo.split(' ', 1)
                if len(partes) != 2:
                    continue
                
                topico, contenido = partes
                mensaje = json.loads(contenido)
                
                self.contador_operaciones += 1
                
                print(f"\n{'='*70}")
                print(f"[Actor-{self.tipo}-Sede{self.sede}] Mensaje #{self.contador_operaciones} recibido")
                
                # Procesar según tipo de tópico
                if topico == 'DEVOLUCION':
                    self.procesar_devolucion(mensaje)
                elif topico == 'RENOVACION':
                    self.procesar_renovacion(mensaje)
                
                print(f"{'='*70}")
                
        except KeyboardInterrupt:
            print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Interrumpido por el usuario")
        finally:
            self.cerrar()
    
    def ejecutar_sincrono(self):
        """
        Loop para actor síncrono (PRÉSTAMO)
        """
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] ¡Esperando solicitudes de préstamo (REQ/REP)!\n")
        
        try:
            while True:
                # Esperar solicitud del GC (bloqueante)
                mensaje_str = self.socket.recv_string()
                
                self.contador_operaciones += 1
                
                print(f"\n{'='*70}")
                print(f"[Actor-{self.tipo}-Sede{self.sede}] Solicitud #{self.contador_operaciones} recibida")
                
                # Parsear mensaje
                try:
                    mensaje = json.loads(mensaje_str)
                except json.JSONDecodeError:
                    respuesta = {
                        'estado': 'ERROR',
                        'mensaje': 'Formato de mensaje inválido',
                        'timestamp': datetime.now().isoformat()
                    }
                    self.socket.send_string(json.dumps(respuesta))
                    continue
                
                # Procesar préstamo
                tiempo_inicio = time.time()
                respuesta = self.procesar_prestamo(mensaje)
                tiempo_proceso = (time.time() - tiempo_inicio) * 1000
                
                # Enviar respuesta al GC
                self.socket.send_string(json.dumps(respuesta))
                
                print(f"[Actor-{self.tipo}-Sede{self.sede}] → Respuesta enviada ({tiempo_proceso:.2f}ms)")
                print(f"{'='*70}")
        
        except KeyboardInterrupt:
            print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Interrumpido por el usuario")
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cierra la conexión ZeroMQ y muestra estadísticas"""
        self.socket.close()
        self.socket_ga.close()
        self.context.term()
        
        print(f"\n{'='*70}")
        print(f"[Actor-{self.tipo}-Sede{self.sede}] Estadísticas Finales:")
        print(f"  Total operaciones: {self.contador_operaciones}")
        print(f"  Exitosas: {self.operaciones_exitosas}")
        print(f"  Fallidas: {self.operaciones_fallidas}")
        if self.contador_operaciones > 0:
            tasa = (self.operaciones_exitosas / self.contador_operaciones) * 100
            print(f"  Tasa de éxito: {tasa:.1f}%")
        print(f"{'='*70}")


def main():
    if len(sys.argv) < 3:
        print("Uso: python actor.py <tipo> <sede> [gc_host] [gc_port] [ga_host] [ga_port] [puerto_rep]")
        print("\nTipo: DEVOLUCION, RENOVACION o PRESTAMO")
        print("\nEjemplos:")
        print("  # Actor Devolución (asíncrono - SUB)")
        print("  python actor.py DEVOLUCION 1 localhost 5556 localhost 5560")
        print("\n  # Actor Renovación (asíncrono - SUB)")
        print("  python actor.py RENOVACION 1 localhost 5556 localhost 5560")
        print("\n  # Actor Préstamo (síncrono - REP)")
        print("  python actor.py PRESTAMO 1 localhost 5556 localhost 5560 5559")
        sys.exit(1)
    
    tipo = sys.argv[1]
    sede = int(sys.argv[2])
    gc_host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    gc_port = int(sys.argv[4]) if len(sys.argv) > 4 else 5556
    ga_host = sys.argv[5] if len(sys.argv) > 5 else "localhost"
    ga_port = int(sys.argv[6]) if len(sys.argv) > 6 else (5560 if sede == 1 else 5561)
    puerto_rep = int(sys.argv[7]) if len(sys.argv) > 7 else None
    
    actor = Actor(tipo, sede, gc_host, gc_port, ga_host, ga_port, puerto_rep)
    actor.ejecutar()


if __name__ == "__main__":
    main()