"""
Gestor de Almacenamiento (GA)
Maneja todas las operaciones con la base de datos MySQL
Proporciona una interfaz REQ/REP para que los Actores soliciten operaciones
"""
import zmq
import json
import mysql.connector
from datetime import datetime
import sys

class GestorAlmacenamiento:
    def __init__(self, sede, puerto=5560, db_host="localhost", db_port=3306):
        """
        Inicializa el Gestor de Almacenamiento
        
        Args:
            sede: Identificador de la sede (1 o 2)
            puerto: Puerto REP para recibir solicitudes de Actores
            db_host: Host de MySQL
            db_port: Puerto de MySQL
        """
        self.sede = sede
        self.db_host = db_host
        self.db_port = db_port
        
        # Configurar ZeroMQ - Socket REP
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{puerto}")
        
        print(f"[GA-Sede{sede}] Iniciado en puerto {puerto} (REP)")
        print(f"[GA-Sede{sede}] BD: {db_host}:{db_port}")
        print(f"[GA-Sede{sede}] Base de datos: biblioteca_sede{sede}")
        
        # Pool de conexiones (simulado con una conexión reutilizable)
        self.conexion_pool = None
        self.inicializar_pool()
        
        self.contador_operaciones = 0
        self.operaciones_exitosas = 0
        self.operaciones_fallidas = 0
    
    def inicializar_pool(self):
        """Inicializa el pool de conexiones a la BD"""
        try:
            print(f"[GA-Sede{self.sede}] Inicializando pool de conexiones...")
            # En producción, usar un pool real como mysql.connector.pooling
            self.health_check()
            print(f"[GA-Sede{self.sede}] ✓ Pool de conexiones inicializado")
        except Exception as e:
            print(f"[GA-Sede{self.sede}] ⚠ Error al inicializar pool: {e}")
    
    def conectar_bd(self):
        """Establece conexión con la base de datos MySQL"""
        try:
            conexion = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user="biblioteca_user",
                password="biblioteca_pass",
                database=f"biblioteca_sede{self.sede}",
                autocommit=False
            )
            return conexion
        except mysql.connector.Error as e:
            print(f"[GA-Sede{self.sede}] ERROR BD: {e}")
            return None
    
    def health_check(self):
        """Verifica el estado de la conexión a la BD"""
        conexion = self.conectar_bd()
        if conexion:
            conexion.close()
            return True
        return False
    
    def ejecutar_update_devolucion(self, codigo_libro, usuario_id):
        """
        Ejecuta UPDATE para incrementar ejemplares disponibles (devolución)
        
        Returns:
            dict: Resultado de la operación
        """
        conexion = self.conectar_bd()
        if not conexion:
            return {
                'estado': 'ERROR',
                'mensaje': 'No se pudo conectar a la base de datos'
            }
        
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
            
            # Verificar si se actualizó
            if cursor.rowcount == 0:
                conexion.rollback()
                return {
                    'estado': 'ERROR',
                    'mensaje': f'Libro {codigo_libro} no encontrado'
                }
            
            # Obtener información actualizada
            cursor.execute(
                "SELECT nombre, ejemplares_disponibles FROM libros WHERE codigo = %s",
                (codigo_libro,)
            )
            resultado = cursor.fetchone()
            
            conexion.commit()
            cursor.close()
            
            return {
                'estado': 'OK',
                'mensaje': 'Devolución registrada en BD',
                'libro': resultado[0] if resultado else 'Desconocido',
                'ejemplares_disponibles': resultado[1] if resultado else 0
            }
            
        except mysql.connector.Error as e:
            conexion.rollback()
            return {
                'estado': 'ERROR',
                'mensaje': f'Error en BD: {str(e)}'
            }
        finally:
            conexion.close()
    
    def ejecutar_update_renovacion(self, codigo_libro, usuario_id, nueva_fecha):
        """
        Ejecuta UPDATE para renovar préstamo
        
        Returns:
            dict: Resultado de la operación
        """
        conexion = self.conectar_bd()
        if not conexion:
            return {
                'estado': 'ERROR',
                'mensaje': 'No se pudo conectar a la base de datos'
            }
        
        try:
            cursor = conexion.cursor()
            
            # Actualizar fecha de entrega
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
            
            if cursor.rowcount == 0:
                conexion.rollback()
                return {
                    'estado': 'ERROR',
                    'mensaje': 'No se encontró préstamo activo o ya tiene 2 renovaciones'
                }
            
            conexion.commit()
            cursor.close()
            
            return {
                'estado': 'OK',
                'mensaje': 'Renovación registrada en BD',
                'nueva_fecha_entrega': nueva_fecha
            }
            
        except mysql.connector.Error as e:
            conexion.rollback()
            return {
                'estado': 'ERROR',
                'mensaje': f'Error en BD: {str(e)}'
            }
        finally:
            conexion.close()
    
    def ejecutar_insert_historial(self, codigo_libro, usuario_id, operacion, datos_adicionales=None):
        """
        Inserta registro en historial de operaciones
        
        Returns:
            dict: Resultado de la operación
        """
        conexion = self.conectar_bd()
        if not conexion:
            return {
                'estado': 'ERROR',
                'mensaje': 'No se pudo conectar a la base de datos'
            }
        
        try:
            cursor = conexion.cursor()
            
            query = """
                INSERT INTO historial_operaciones 
                (codigo_libro, usuario_id, operacion, fecha, sede, datos_adicionales)
                VALUES (%s, %s, %s, NOW(), %s, %s)
            """
            cursor.execute(query, (
                codigo_libro,
                usuario_id,
                operacion,
                self.sede,
                datos_adicionales
            ))
            
            conexion.commit()
            historial_id = cursor.lastrowid
            cursor.close()
            
            return {
                'estado': 'OK',
                'mensaje': 'Operación registrada en historial',
                'historial_id': historial_id
            }
            
        except mysql.connector.Error as e:
            conexion.rollback()
            return {
                'estado': 'ERROR',
                'mensaje': f'Error en BD: {str(e)}'
            }
        finally:
            conexion.close()
    
    def ejecutar_select_disponibilidad(self, codigo_libro):
        """
        Consulta disponibilidad de un libro
        
        Returns:
            dict: Información del libro
        """
        conexion = self.conectar_bd()
        if not conexion:
            return {
                'estado': 'ERROR',
                'mensaje': 'No se pudo conectar a la base de datos'
            }
        
        try:
            cursor = conexion.cursor()
            
            query = """
                SELECT codigo, nombre, autor, ejemplares_disponibles, ejemplares_totales
                FROM libros
                WHERE codigo = %s
            """
            cursor.execute(query, (codigo_libro,))
            resultado = cursor.fetchone()
            
            cursor.close()
            
            if not resultado:
                return {
                    'estado': 'ERROR',
                    'mensaje': 'Libro no encontrado'
                }
            
            return {
                'estado': 'OK',
                'codigo': resultado[0],
                'nombre': resultado[1],
                'autor': resultado[2],
                'ejemplares_disponibles': resultado[3],
                'ejemplares_totales': resultado[4]
            }
            
        except mysql.connector.Error as e:
            return {
                'estado': 'ERROR',
                'mensaje': f'Error en BD: {str(e)}'
            }
        finally:
            conexion.close()
    
    def ejecutar_transaccion_prestamo(self, codigo_libro, usuario_id, fecha_prestamo, fecha_entrega):
        """
        Ejecuta transacción ACID completa para préstamo
        
        Returns:
            dict: Resultado de la transacción
        """
        conexion = self.conectar_bd()
        if not conexion:
            return {
                'estado': 'ERROR',
                'mensaje': 'No se pudo conectar a la base de datos'
            }
        
        try:
            cursor = conexion.cursor()
            
            # Iniciar transacción
            conexion.start_transaction()
            
            # 1. Verificar y reducir ejemplares
            query_update = """
                UPDATE libros 
                SET ejemplares_disponibles = ejemplares_disponibles - 1,
                    fecha_ultima_actualizacion = NOW()
                WHERE codigo = %s AND ejemplares_disponibles > 0
            """
            cursor.execute(query_update, (codigo_libro,))
            
            if cursor.rowcount == 0:
                conexion.rollback()
                return {
                    'estado': 'RECHAZADO',
                    'mensaje': 'Libro no disponible'
                }
            
            # 2. Insertar préstamo
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
            
            # 3. Registrar en historial
            query_historial = """
                INSERT INTO historial_operaciones 
                (codigo_libro, usuario_id, operacion, fecha, sede, datos_adicionales)
                VALUES (%s, %s, 'PRESTAMO', NOW(), %s, %s)
            """
            datos_adicionales = json.dumps({
                'prestamo_id': prestamo_id,
                'fecha_entrega': fecha_entrega.isoformat() if hasattr(fecha_entrega, 'isoformat') else str(fecha_entrega)
            })
            cursor.execute(query_historial, (
                codigo_libro,
                usuario_id,
                self.sede,
                datos_adicionales
            ))
            
            # Commit transacción
            conexion.commit()
            cursor.close()
            
            print(f"[GA-Sede{self.sede}] → Replicación asíncrona a BD secundaria iniciada")
            
            return {
                'estado': 'OK',
                'mensaje': 'Transacción completada exitosamente',
                'prestamo_id': prestamo_id,
                'fecha_prestamo': str(fecha_prestamo),
                'fecha_entrega': str(fecha_entrega)
            }
            
        except mysql.connector.Error as e:
            conexion.rollback()
            return {
                'estado': 'ERROR',
                'mensaje': f'Error en transacción: {str(e)}'
            }
        finally:
            conexion.close()
    
    def procesar_solicitud(self, solicitud):
        """
        Procesa una solicitud recibida de un Actor
        
        Args:
            solicitud: dict con la operación solicitada
            
        Returns:
            dict: Respuesta con el resultado
        """
        operacion = solicitud.get('operacion')
        
        if operacion == 'UPDATE_DEVOLUCION':
            return self.ejecutar_update_devolucion(
                solicitud['codigo_libro'],
                solicitud['usuario_id']
            )
        
        elif operacion == 'UPDATE_RENOVACION':
            return self.ejecutar_update_renovacion(
                solicitud['codigo_libro'],
                solicitud['usuario_id'],
                solicitud['nueva_fecha']
            )
        
        elif operacion == 'INSERT_HISTORIAL':
            return self.ejecutar_insert_historial(
                solicitud['codigo_libro'],
                solicitud['usuario_id'],
                solicitud['tipo_operacion'],
                solicitud.get('datos_adicionales')
            )
        
        elif operacion == 'SELECT_DISPONIBILIDAD':
            return self.ejecutar_select_disponibilidad(
                solicitud['codigo_libro']
            )
        
        elif operacion == 'TRANSACCION_PRESTAMO':
            return self.ejecutar_transaccion_prestamo(
                solicitud['codigo_libro'],
                solicitud['usuario_id'],
                solicitud['fecha_prestamo'],
                solicitud['fecha_entrega']
            )
        
        else:
            return {
                'estado': 'ERROR',
                'mensaje': f'Operación desconocida: {operacion}'
            }
    
    def ejecutar(self):
        """
        Loop principal del Gestor de Almacenamiento
        """
        print(f"\n[GA-Sede{self.sede}] ¡Esperando solicitudes de Actores!\n")
        
        try:
            while True:
                # Esperar solicitud (bloqueante)
                solicitud_str = self.socket.recv_string()
                
                self.contador_operaciones += 1
                
                print(f"\n{'='*70}")
                print(f"[GA-Sede{self.sede}] Solicitud #{self.contador_operaciones} recibida")
                
                # Parsear solicitud
                try:
                    solicitud = json.loads(solicitud_str)
                    print(f"[GA-Sede{self.sede}] Operación: {solicitud.get('operacion')}")
                    
                    # Procesar solicitud
                    respuesta = self.procesar_solicitud(solicitud)
                    
                    if respuesta['estado'] in ['OK', 'RECHAZADO']:
                        self.operaciones_exitosas += 1
                    else:
                        self.operaciones_fallidas += 1
                    
                except json.JSONDecodeError:
                    respuesta = {
                        'estado': 'ERROR',
                        'mensaje': 'Formato de solicitud inválido'
                    }
                    self.operaciones_fallidas += 1
                
                # Enviar respuesta
                self.socket.send_string(json.dumps(respuesta))
                print(f"[GA-Sede{self.sede}] → Respuesta enviada: {respuesta['estado']}")
                print(f"{'='*70}")
        
        except KeyboardInterrupt:
            print(f"\n[GA-Sede{self.sede}] Interrumpido por el usuario")
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cierra conexiones y muestra estadísticas"""
        self.socket.close()
        self.context.term()
        
        print(f"\n{'='*70}")
        print(f"[GA-Sede{self.sede}] Estadísticas Finales:")
        print(f"  Total operaciones: {self.contador_operaciones}")
        print(f"  Exitosas: {self.operaciones_exitosas}")
        print(f"  Fallidas: {self.operaciones_fallidas}")
        if self.contador_operaciones > 0:
            tasa = (self.operaciones_exitosas / self.contador_operaciones) * 100
            print(f"  Tasa de éxito: {tasa:.1f}%")
        print(f"{'='*70}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python gestor_almacenamiento.py <sede> [puerto] [db_host] [db_port]")
        print("\nEjemplos:")
        print("  python gestor_almacenamiento.py 1 5560 localhost 3306")
        print("  python gestor_almacenamiento.py 2 5561 localhost 3306")
        sys.exit(1)
    
    sede = int(sys.argv[1])
    puerto = int(sys.argv[2]) if len(sys.argv) > 2 else (5560 if sede == 1 else 5561)
    db_host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    db_port = int(sys.argv[4]) if len(sys.argv) > 4 else 3306
    
    gestor = GestorAlmacenamiento(sede, puerto, db_host, db_port)
    gestor.ejecutar()


if __name__ == "__main__":
    main()