"""
Actor
Procesa tópicos de DEVOLUCION y RENOVACION y actualiza la BD
"""
import zmq
import json
import mysql.connector
from datetime import datetime
import time

class Actor:
    def __init__(self, tipo, sede, gc_host="localhost", gc_port=5556, 
                 db_host="localhost", db_port=3306):
        """
        Inicializa el Actor
        
        Args:
            tipo: Tipo de actor ('DEVOLUCION' o 'RENOVACION')
            sede: Identificador de la sede
            gc_host: Host del Gestor de Carga
            gc_port: Puerto del publisher del GC
            db_host: Host de MySQL
            db_port: Puerto de MySQL
        """
        self.tipo = tipo.upper()
        self.sede = sede
        self.db_host = db_host
        self.db_port = db_port
        
        # Configurar ZeroMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{gc_host}:{gc_port}")
        
        # Suscribirse al tópico correspondiente
        self.socket.setsockopt_string(zmq.SUBSCRIBE, self.tipo)
        
        print(f"[Actor-{self.tipo}-Sede{sede}] Iniciado")
        print(f"[Actor-{self.tipo}-Sede{sede}] Conectado a GC: {gc_host}:{gc_port}")
        print(f"[Actor-{self.tipo}-Sede{sede}] Suscrito al tópico: {self.tipo}")
        print(f"[Actor-{self.tipo}-Sede{sede}] BD: {db_host}:{db_port}")
        
        self.contador_operaciones = 0
    
    def conectar_bd(self):
        """Establece conexión con la base de datos MySQL"""
        try:
            conexion = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user="biblioteca_user",
                password="biblioteca_pass",
                database=f"biblioteca_sede{self.sede}"
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
        
        print(f"[Actor-{self.tipo}-Sede{self.sede}] Procesando devolución:")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        
        conexion = self.conectar_bd()
        if not conexion:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ No se pudo conectar a la BD")
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
            
            cursor.close()
            
        except mysql.connector.Error as e:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en BD: {e}")
            conexion.rollback()
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
        
        print(f"[Actor-{self.tipo}-Sede{self.sede}] Procesando renovación:")
        print(f"  → Libro: {codigo_libro}")
        print(f"  → Usuario: {usuario_id}")
        print(f"  → Nueva fecha: {nueva_fecha}")
        
        conexion = self.conectar_bd()
        if not conexion:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ No se pudo conectar a la BD")
            return
        
        try:
            cursor = conexion.cursor()
            
            # Actualizar fecha de entrega en préstamos activos
            # (Nota: esta tabla se implementará según el diseño completo)
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
            else:
                print(f"[Actor-{self.tipo}-Sede{self.sede}] ⚠ No se encontró préstamo activo o ya tiene 2 renovaciones")
            
            cursor.close()
            
        except mysql.connector.Error as e:
            print(f"[Actor-{self.tipo}-Sede{self.sede}] ✗ Error en BD: {e}")
            conexion.rollback()
        finally:
            conexion.close()
    
    def ejecutar(self):
        """
        Ejecuta el loop principal del Actor
        Espera y procesa mensajes del tópico suscrito
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
                
                print(f"\n{'='*60}")
                print(f"[Actor-{self.tipo}-Sede{self.sede}] Mensaje #{self.contador_operaciones} recibido")
                
                # Procesar según tipo de tópico
                if topico == 'DEVOLUCION':
                    self.procesar_devolucion(mensaje)
                elif topico == 'RENOVACION':
                    self.procesar_renovacion(mensaje)
                
                print(f"{'='*60}")
                
        except KeyboardInterrupt:
            print(f"\n[Actor-{self.tipo}-Sede{self.sede}] Interrumpido por el usuario")
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cierra la conexión ZeroMQ"""
        self.socket.close()
        self.context.term()
        print(f"[Actor-{self.tipo}-Sede{self.sede}] Conexión cerrada")
        print(f"[Actor-{self.tipo}-Sede{self.sede}] Total operaciones procesadas: {self.contador_operaciones}")


def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python actor.py <tipo> <sede> [gc_host] [gc_port] [db_host] [db_port]")
        print("Tipo: DEVOLUCION o RENOVACION")
        print("Ejemplo: python actor.py DEVOLUCION 1 localhost 5556 localhost 3306")
        sys.exit(1)
    
    tipo = sys.argv[1]
    sede = int(sys.argv[2])
    gc_host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
    gc_port = int(sys.argv[4]) if len(sys.argv) > 4 else 5556
    db_host = sys.argv[5] if len(sys.argv) > 5 else "localhost"
    db_port = int(sys.argv[6]) if len(sys.argv) > 6 else 3306
    
    actor = Actor(tipo, sede, gc_host, gc_port, db_host, db_port)
    actor.ejecutar()


if __name__ == "__main__":
    main()