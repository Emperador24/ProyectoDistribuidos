"""
Actor Unificado
Procesa DEVOLUCION, RENOVACION (asíncronas) y PRESTAMO (síncrona)
"""
import zmq
import json
import mysql.connector
from datetime import datetime, timedelta
import time
import sys

class Actor:
    def __init__(self, tipo, sede, gc_host="localhost", gc_port=5556, 
                 db_host="localhost", db_port=3306, puerto_rep=None):
        """
        Inicializa el Actor
        
        Args:
            tipo: Tipo de actor ('DEVOLUCION', 'RENOVACION' o 'PRESTAMO')
            sede: Identificador de la sede
            gc_host: Host del Gestor de Carga
            gc_port: Puerto del publisher del GC (para SUB) o puerto propio (para REP)
            db_host: Host de MySQL
            db_port: Puerto de MySQL
            puerto_rep: Puerto REP si es actor de préstamo (ej: 5559)
        """
        self.tipo = tipo.upper()
        self.sede = sede
        self.db_host = db_host
        self.db_port = db_port
        
        # Configurar ZeroMQ según el tipo
        self.context = zmq.Context()
        
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
        
        print(f"[Actor-{self.tipo}-Sede{sede}] BD: {db_host}:{db_port}")
        
        self.contador_operaciones = 0
        self.operaciones_exitosas = 0
        self.operaciones_fallidas = 0
    
    def conectar_bd(self):
        """Establece conexión con la base de datos MySQL"""
        try:
            conexion = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user="biblioteca_user",
                password="biblioteca_pass",
                database=f"biblioteca_sede{self.sede}",
                autocommit=False  # Para transacciones
            )
            return conexion
        except mysql.connector.Error as e:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ERROR BD: {e}")
            return None
    
    def procesar_devolucion(self, mensaje):
        """
        Procesa una devolución de libro y actualiza la BD
        Incrementa el número de ejemplares disponibles
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        timestamp = mensaje['timestamp']
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando devolución:")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        
        conexion = self.conectar_bd()
        if not conexion:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ No se pudo conectar a la BD")
            self.operaciones_fallidas += 1
            return
        
        try:
            cursor = conexion.cursor()
            
            # Incrementar ejemplares disponibles
            query = """
                UPDATE libros 
                SET ejemplares_disponibles = ejemplares_disponibles + 1,
                    fecha_ultima_actualizacion = NOW()
                WHERE codigo = %s
            """
            cursor.execute(query, (codigo_libro,))
            
            # Registrar la operación en el historial
            query_historial = """
                INSERT INTO historial_operaciones 
                (codigo_libro, usuario_id, operacion, fecha, sede)
                VALUES (%s, %s, %s, NOW(), %s)
            """
            cursor.execute(query_historial, 
                          (codigo_libro, usuario_id, 'DEVOLUCION', self.sede))
            
            conexion.commit()
            
            # Verificar actualización
            cursor.execute(
                "SELECT nombre, ejemplares_disponibles FROM libros WHERE codigo = %s",
                (codigo_libro,)
            )
            resultado = cursor.fetchone()
            
            if resultado:
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ BD actualizada:")
                print(f"  → Libro: {resultado[0]}")
                print(f"  → Ejemplares disponibles: {resultado[1]}")
                print(f"[Actor-{self.tipo}-Sede{self.sede}] → Replicación asíncrona a BD secundaria iniciada")
                self.operaciones_exitosas += 1
            
            cursor.close()
            
        except mysql.connector.Error as e:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en BD: {e}")
            conexion.rollback()
            self.operaciones_fallidas += 1
        finally:
            conexion.close()
    
    def procesar_renovacion(self, mensaje):
        """
        Procesa una renovación de libro y actualiza la BD
        Actualiza la fecha de entrega del préstamo
        """
        codigo_libro = mensaje['codigo_libro']
        usuario_id = mensaje['usuario_id']
        nueva_fecha = mensaje['nueva_fecha_entrega']
        
        print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Procesando renovación:")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        print(f"  → Nueva fecha: {nueva_fecha}")
        
        conexion = self.conectar_bd()
        if not conexion:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ No se pudo conectar a la BD")
            self.operaciones_fallidas += 1
            return
        
        try:
            cursor = conexion.cursor()
            
            # Actualizar fecha de entrega en préstamos activos
            query = """
                UPDATE prestamos 
                SET fecha_entrega = %s,
                    renovaciones = renovaciones + 1,
                    fecha_ultima_actualizacion = NOW()
                WHERE codigo_libro = %s 
                  AND usuario_id = %s 
                  AND estado = 'ACTIVO'
                  AND renovaciones < 2
            """
            cursor.execute(query, (nueva_fecha, codigo_libro, usuario_id))
            
            # Registrar la operación
            query_historial = """
                INSERT INTO historial_operaciones 
                (codigo_libro, usuario_id, operacion, fecha, sede, datos_adicionales)
                VALUES (%s, %s, %s, NOW(), %s, %s)
            """
            datos_adicionales = json.dumps({'nueva_fecha_entrega': nueva_fecha})
            cursor.execute(query_historial, 
                          (codigo_libro, usuario_id, 'RENOVACION', self.sede, 
                           datos_adicionales))
            
            conexion.commit()
            
            if cursor.rowcount > 0:
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Renovación registrada en BD")
                print(f"[Actor-{self.tipo}-Sede{self.sede}] → Replicación asíncrona a BD secundaria iniciada")
                self.operaciones_exitosas += 1
            else:
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ⚠ No se encontró préstamo activo o ya tiene 2 renovaciones")
                self.operaciones_fallidas += 1
            
            cursor.close()
            
        except mysql.connector.Error as e:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en BD: {e}")
            conexion.rollback()
            self.operaciones_fallidas += 1
        finally:
            conexion.close()
    
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
        
        conexion = self.conectar_bd()
        if not conexion:
            self.operaciones_fallidas += 1
            return {
                'estado': 'ERROR',
                'mensaje': 'No se pudo conectar a la base de datos',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            cursor = conexion.cursor()
            
            # PASO 1: Verificar disponibilidad
            print(f"[Actor-{self.tipo}-Sede{self.sede}] → Verificando disponibilidad en BD...")
            query_verificar = """
                SELECT codigo, nombre, autor, ejemplares_disponibles, ejemplares_totales
                FROM libros
                WHERE codigo = %s
            """
            cursor.execute(query_verificar, (codigo_libro,))
            resultado = cursor.fetchone()
            
            if not resultado:
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Libro no encontrado")
                cursor.close()
                conexion.close()
                self.operaciones_fallidas += 1
                return {
                    'estado': 'RECHAZADO',
                    'mensaje': 'Libro no encontrado en la biblioteca',
                    'codigo_libro': codigo_libro,
                    'timestamp': datetime.now().isoformat()
                }
            
            codigo, nombre, autor, disponibles, totales = resultado
            
            if disponibles <= 0:
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Sin ejemplares disponibles (0/{totales})")
                cursor.close()
                conexion.close()
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
            
            # PASO 2: Iniciar transacción ACID
            print(f"[Actor-{self.tipo}-Sede{self.sede}] → Iniciando transacción ACID...")
            conexion.start_transaction()
            
            # PASO 3: Reducir ejemplares disponibles
            query_update = """
                UPDATE libros 
                SET ejemplares_disponibles = ejemplares_disponibles - 1,
                    fecha_ultima_actualizacion = NOW()
                WHERE codigo = %s AND ejemplares_disponibles > 0
            """
            cursor.execute(query_update, (codigo_libro,))
            
            if cursor.rowcount == 0:
                # Race condition: otro proceso tomó el último ejemplar
                conexion.rollback()
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Race condition: libro ya no disponible")
                cursor.close()
                conexion.close()
                self.operaciones_fallidas += 1
                return {
                    'estado': 'RECHAZADO',
                    'mensaje': 'Libro ya no disponible (tomado por otro usuario)',
                    'codigo_libro': codigo_libro,
                    'timestamp': datetime.now().isoformat()
                }
            
            print(f"[Actor-{self.tipo}-Sede{self.sede}]   ✓ UPDATE libros (ejemplares -= 1)")
            
            # PASO 4: Calcular fechas
            fecha_prestamo = datetime.now()
            fecha_entrega = fecha_prestamo + timedelta(weeks=2)
            
            # PASO 5: Insertar préstamo
            query_prestamo = """
                INSERT INTO prestamos 
                (codigo_libro, usuario_id, fecha_prestamo, fecha_entrega, 
                 renovaciones, estado, sede)
                VALUES (%s, %s, %s, %s, 0, 'ACTIVO', %s)
            """
            cursor.execute(query_prestamo, (
                codigo_libro,
                usuario_id,
                fecha_prestamo,
                fecha_entrega,
                self.sede
            ))
            
            prestamo_id = cursor.lastrowid
            print(f"[Actor-{self.tipo}-Sede{self.sede}]   ✓ INSERT prestamos (ID: {prestamo_id})")
            
            # PASO 6: Registrar en historial
            query_historial = """
                INSERT INTO historial_operaciones 
                (codigo_libro, usuario_id, operacion, fecha, sede, datos_adicionales)
                VALUES (%s, %s, 'PRESTAMO', NOW(), %s, %s)
            """
            datos_adicionales = json.dumps({
                'prestamo_id': prestamo_id,
                'fecha_entrega': fecha_entrega.isoformat(),
                'ejemplares_restantes': disponibles - 1
            })
            cursor.execute(query_historial, (
                codigo_libro,
                usuario_id,
                self.sede,
                datos_adicionales
            ))
            
            print(f"[Actor-{self.tipo}-Sede{self.sede}]   ✓ INSERT historial_operaciones")
            
            # PASO 7: Commit transacción
            conexion.commit()
            print(f"[Actor-{self.tipo}-Sede{self.sede}]   ✓ COMMIT exitoso")
            print(f"[Actor-{self.tipo}-Sede{self.sede}] → Replicación asíncrona a BD secundaria iniciada")
            
            self.operaciones_exitosas += 1
            
            # PASO 8: Preparar respuesta exitosa
            respuesta = {
                'estado': 'OK',
                'mensaje': f'Préstamo otorgado exitosamente',
                'codigo_libro': codigo_libro,
                'nombre_libro': nombre,
                'fecha_prestamo': fecha_prestamo.strftime('%Y-%m-%d'),
                'fecha_entrega': fecha_entrega.strftime('%Y-%m-%d'),
                'prestamo_id': prestamo_id,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✓ Préstamo exitoso")
            print(f"[Actor-{self.tipo}-Sede{self.sede}]   Fecha entrega: {fecha_entrega.strftime('%Y-%m-%d')}")
            
            cursor.close()
            return respuesta
            
        except mysql.connector.Error as e:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en BD: {e}")
            conexion.rollback()
            self.operaciones_fallidas += 1
            
            return {
                'estado': 'ERROR',
                'mensaje': f'Error en base de datos: {str(e)}',
                'codigo_libro': codigo_libro,
                'timestamp': datetime.now().isoformat()
            }
        
        finally:
            conexion.close()
    
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
        print("Uso: python actor.py <tipo> <sede> [gc_host] [gc_port] [db_host] [db_port] [puerto_rep]")
        print("\nTipo: DEVOLUCION, RENOVACION o PRESTAMO")
        print("\nEjemplos:")
        print("  # Actor Devolución (asíncrono - SUB)")
        print("  python actor.py DEVOLUCION 1 localhost 5556 localhost 3306")
        print("\n  # Actor Renovación (asíncrono - SUB)")
        print("  python actor.py RENOVACION 1 localhost 5556 localhost 3306")
        print("\n  # Actor Préstamo (síncrono - REP)")
        print("  python actor.py PRESTAMO 1 localhost 5556 localhost 3306 5559")
        print("  (Nota: gc_port se ignora para PRESTAMO, puerto_rep es el puerto REP)")
        sys.exit(1)
    
    tipo = sys.argv[1]
    sede = int(sys.argv[2])
    gc_host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    gc_port = int(sys.argv[4]) if len(sys.argv) > 4 else 5556
    db_host = sys.argv[5] if len(sys.argv) > 5 else "localhost"
    db_port = int(sys.argv[6]) if len(sys.argv) > 6 else 3306
    puerto_rep = int(sys.argv[7]) if len(sys.argv) > 7 else None
    
    actor = Actor(tipo, sede, gc_host, gc_port, db_host, db_port, puerto_rep)
    actor.ejecutar()


if __name__ == "__main__":
    main()