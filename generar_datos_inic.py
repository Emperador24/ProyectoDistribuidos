"""
Script para generar datos iniciales en la Base de Datos
Carga 1000 libros (50 prestados en sede 1, 150 en sede 2)
"""
import mysql.connector
from datetime import datetime, timedelta
import random

# Datos de ejemplo para generar libros
AUTORES = [
    "Gabriel García Márquez", "Jorge Luis Borges", "Isabel Allende",
    "Mario Vargas Llosa", "Julio Cortázar", "Pablo Neruda",
    "Octavio Paz", "Carlos Fuentes", "Laura Esquivel",
    "Miguel de Cervantes", "Federico García Lorca", "Sor Juana Inés",
    "Roberto Bolaño", "Gioconda Belli", "Gabriela Mistral",
    "Horacio Quiroga", "Juan Rulfo", "Alejo Carpentier"
]

EDITORIALES = [
    "Alfaguara", "Planeta", "Penguin Random House", "Anagrama",
    "Tusquets", "Seix Barral", "Norma", "Debate", "Booket"
]

CATEGORIAS = [
    "Novela", "Cuento", "Poesía", "Ensayo", "Teatro",
    "Ciencia Ficción", "Historia", "Biografía", "Filosofía", "Arte"
]

class GeneradorDatos:
    def __init__(self, host="localhost", port=3306):
        self.host = host
        self.port = port
        
    def conectar(self, database):
        """Conecta a la base de datos especificada"""
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user="biblioteca_user",
            password="biblioteca_pass",
            database=database
        )
    
    def generar_libros(self, cantidad=1000):
        """Genera una lista de libros con datos aleatorios"""
        libros = []
        
        for i in range(1, cantidad + 1):
            # Generar código único
            codigo = f"LIB{i:05d}"
            
            # Generar título
            categoria = random.choice(CATEGORIAS)
            numero = random.randint(1, 999)
            nombre = f"{categoria} {numero}: Historia de la Literatura"
            
            # Seleccionar autor y editorial
            autor = random.choice(AUTORES)
            editorial = random.choice(EDITORIALES)
            
            # Generar ISBN
            isbn = f"978-{random.randint(0, 9)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(0, 9)}"
            
            # Número de ejemplares (algunos tienen 1, otros más)
            ejemplares = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
            
            libros.append({
                'codigo': codigo,
                'nombre': nombre,
                'autor': autor,
                'editorial': editorial,
                'isbn': isbn,
                'ejemplares_totales': ejemplares,
                'ejemplares_disponibles': ejemplares
            })
        
        return libros
    
    def insertar_libros(self, sede, libros):
        """Inserta libros en la base de datos de una sede"""
        database = f"biblioteca_sede{sede}"
        conexion = self.conectar(database)
        cursor = conexion.cursor()
        
        query = """
            INSERT INTO libros 
            (codigo, nombre, autor, editorial, isbn, ejemplares_totales, ejemplares_disponibles)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        print(f"\n[BD] Insertando {len(libros)} libros en {database}...")
        
        for libro in libros:
            cursor.execute(query, (
                libro['codigo'],
                libro['nombre'],
                libro['autor'],
                libro['editorial'],
                libro['isbn'],
                libro['ejemplares_totales'],
                libro['ejemplares_disponibles']
            ))
        
        conexion.commit()
        print(f"[BD] ✓ {len(libros)} libros insertados en {database}")
        
        cursor.close()
        conexion.close()
    
    def generar_prestamos(self, sede, libros, cantidad_prestamos):
        """Genera préstamos activos para algunos libros"""
        database = f"biblioteca_sede{sede}"
        conexion = self.conectar(database)
        cursor = conexion.cursor()
        
        print(f"\n[BD] Generando {cantidad_prestamos} préstamos en {database}...")
        
        # Seleccionar libros al azar para prestar
        libros_prestados = random.sample(libros, min(cantidad_prestamos, len(libros)))
        
        for libro in libros_prestados:
            # Generar usuario aleatorio
            usuario_id = f"USR{random.randint(1000, 9999)}"
            
            # Fecha de préstamo (entre 1 y 14 días atrás)
            dias_atras = random.randint(1, 14)
            fecha_prestamo = datetime.now() - timedelta(days=dias_atras)
            fecha_entrega = fecha_prestamo + timedelta(weeks=2)
            
            # Número de renovaciones (0, 1 o 2)
            renovaciones = random.choice([0, 0, 0, 1, 1, 2])
            
            # Insertar préstamo
            query_prestamo = """
                INSERT INTO prestamos 
                (codigo_libro, usuario_id, fecha_prestamo, fecha_entrega, 
                 renovaciones, estado, sede)
                VALUES (%s, %s, %s, %s, %s, 'ACTIVO', %s)
            """
            cursor.execute(query_prestamo, (
                libro['codigo'],
                usuario_id,
                fecha_prestamo,
                fecha_entrega,
                renovaciones,
                sede
            ))
            
            # Actualizar ejemplares disponibles
            query_update = """
                UPDATE libros 
                SET ejemplares_disponibles = ejemplares_disponibles - 1
                WHERE codigo = %s AND ejemplares_disponibles > 0
            """
            cursor.execute(query_update, (libro['codigo'],))
        
        conexion.commit()
        print(f"[BD] ✓ {cantidad_prestamos} préstamos generados en {database}")
        
        cursor.close()
        conexion.close()
    
    def verificar_datos(self, sede):
        """Verifica los datos insertados en una sede"""
        database = f"biblioteca_sede{sede}"
        conexion = self.conectar(database)
        cursor = conexion.cursor()
        
        # Contar libros
        cursor.execute("SELECT COUNT(*) FROM libros")
        total_libros = cursor.fetchone()[0]
        
        # Contar préstamos activos
        cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'ACTIVO'")
        prestamos_activos = cursor.fetchone()[0]
        
        # Ejemplares disponibles
        cursor.execute("SELECT SUM(ejemplares_disponibles) FROM libros")
        ejemplares_disponibles = cursor.fetchone()[0]
        
        print(f"\n[BD] Resumen {database}:")
        print(f"  → Total de libros: {total_libros}")
        print(f"  → Préstamos activos: {prestamos_activos}")
        print(f"  → Ejemplares disponibles: {ejemplares_disponibles}")
        
        cursor.close()
        conexion.close()
    
    def ejecutar(self):
        """Ejecuta la generación completa de datos"""
        print("="*60)
        print("GENERADOR DE DATOS INICIALES")
        print("Sistema de Préstamo de Libros - Universidad Ada Lovelace")
        print("="*60)
        
        # Generar 1000 libros
        print("\n[1] Generando 1000 libros...")
        libros = self.generar_libros(1000)
        print(f"✓ 1000 libros generados")
        
        # Insertar en ambas sedes (datos idénticos inicialmente)
        print("\n[2] Insertando libros en ambas sedes...")
        self.insertar_libros(1, libros)
        self.insertar_libros(2, libros)
        
        # Generar préstamos: 50 en sede 1, 150 en sede 2
        print("\n[3] Generando préstamos...")
        self.generar_prestamos(1, libros, 50)
        self.generar_prestamos(2, libros, 150)
        
        # Verificar datos
        print("\n[4] Verificando datos insertados...")
        self.verificar_datos(1)
        self.verificar_datos(2)
        
        print("\n" + "="*60)
        print("✓ DATOS INICIALES GENERADOS EXITOSAMENTE")
        print("="*60)


def main():
    import sys
    
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 3306
    
    generador = GeneradorDatos(host, port)
    
    try:
        generador.ejecutar()
    except mysql.connector.Error as e:
        print(f"\n[ERROR] Error de base de datos: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()