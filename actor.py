"""
Actor Unificado
Procesa DEVOLUCION, RENOVACION y PRESTAMO (todas síncronas con REP)
Se comunica con el Gestor de Almacenamiento (GA) mediante REQ/REP
"""
import zmq
import json
from datetime import datetime, timedelta
import time
import sys

class Actor:
    def __init__(self, tipo, sede, puerto_rep, ga_host="localhost", ga_port=5560):
        """
        Inicializa el Actor
        
        Args:
            tipo: Tipo de actor ('DEVOLUCION', 'RENOVACION' o 'PRESTAMO')
            sede: Identificador de la sede
            puerto_rep: Puerto REP para recibir solicitudes del GC
            ga_host: Host del Gestor de Almacenamiento
            ga_port: Puerto del Gestor de Almacenamiento
        """
        self.tipo = tipo.upper()
        self.sede = sede
        self.ga_host = ga_host
        self.ga_port = ga_port
        
        # Configurar ZeroMQ
        self.context = zmq.Context()
        
        # Socket REP para recibir solicitudes del GC (todos los actores usan REP ahora)
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{puerto_rep}")
        print(f"[Actor-{self.tipo}-Sede{sede}] Iniciado en puerto {puerto_rep} (REP - Síncrono)")
        
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
        Procesa una devolución de libro solicitando al GA (SÍNCRONO)
        
        Returns:
            dict: Respuesta con estado de la devolución
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        timestamp = mensaje['timestamp']
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando devolución (SÍNCRONO):")
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
            return {
                'estado': 'ERROR',
                'mensaje': respuesta_update['mensaje'],
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
        
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
            
            return {
                'estado': 'OK',
                'mensaje': 'Devolución procesada exitosamente',
                'codigo_libro': codigo_libro,
                'libro': respuesta_update.get('libro', ''),
                'ejemplares_disponibles': respuesta_update.get('ejemplares_disponibles', 0),
                'timestamp': datetime.now().isoformat()
            }
        else:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ⚠ No se pudo registrar en historial")
            self.operaciones_fallidas += 1
            return {
                'estado': 'ERROR',
                'mensaje': 'Error al registrar en historial',
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
    
    def procesar_renovacion(self, mensaje):
        """
        Procesa una renovación de libro solicitando al GA (SÍNCRONO)
        
        Returns:
            dict: Respuesta con estado de la renovación
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        nueva_fecha = mensaje['nueva_fecha_entrega']
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando renovación (SÍNCRONO):")
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
            return {
                'estado': 'ERROR',
                'mensaje': respuesta_update['mensaje'],
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
        
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
            
            return {
                'estado': 'OK',
                'mensaje': 'Renovación procesada exitosamente',
                'codigo_libro': codigo_libro,
                'nueva_fecha_entrega': nueva_fecha,
                'timestamp': datetime.now().isoformat()
            }
        else:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ⚠ No se pudo registrar en historial")
            self.operaciones_fallidas += 1
            return {
                'estado': 'ERROR',
                'mensaje': 'Error al registrar en historial',
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
    
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
        Loop principal del Actor (todos son síncronos ahora)
        """
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] ¡Esperando solicitudes (REQ/REP)!\n")
        
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
                
                # Procesar según tipo de actor
                tiempo_inicio = time.time()
                
                if self.tipo == 'DEVOLUCION':
                    respuesta = self.procesar_devolucion(mensaje)
                elif self.tipo == 'RENOVACION':
                    respuesta = self.procesar_renovacion(mensaje)
                elif self.tipo == 'PRESTAMO':
                    respuesta = self.procesar_prestamo(mensaje)
                else:
                    respuesta = {
                        'estado': 'ERROR',
                        'mensaje': f'Tipo de actor desconocido: {self.tipo}',
                        'timestamp': datetime.now().isoformat()
                    }
                
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
    if len(sys.argv) < 4:
        print("Uso: python actor.py <tipo> <sede> <puerto_rep> [ga_host] [ga_port]")
        print("\nTipo: DEVOLUCION, RENOVACION o PRESTAMO")
        print("\nEjemplos:")
        print("  # Actor Devolución (síncrono - REP)")
        print("  python actor.py DEVOLUCION 1 5556 localhost 5560")
        print("\n  # Actor Renovación (síncrono - REP)")
        print("  python actor.py RENOVACION 1 5557 localhost 5560")
        print("\n  # Actor Préstamo (síncrono - REP)")
        print("  python actor.py PRESTAMO 1 5559 localhost 5560")
        sys.exit(1)
    
    tipo = sys.argv[1]
    sede = int(sys.argv[2])
    puerto_rep = int(sys.argv[3])
    ga_host = sys.argv[4] if len(sys.argv) > 4 else "localhost"
    ga_port = int(sys.argv[5]) if len(sys.argv) > 5 else (5560 if sede == 1 else 5561)
    
    actor = Actor(tipo, sede, puerto_rep, ga_host, ga_port)
    actor.ejecutar()


if __name__ == "__main__":
    main()