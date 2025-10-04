"""
Script de prueba para verificar el funcionamiento del sistema
Permite probar la conexión a BD y verificar datos
"""
import mysql.connector
from datetime import datetime
import sys

class TestSistema:
    def __init__(self, host="localhost", port=3306):
        self.host = host
        self.port = port
    
    def conectar(self, sede):
        """Conecta a la base de datos de una sede"""
        try:
            conexion = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user="biblioteca_user",
                password="biblioteca_pass",
                database=f"biblioteca_sede{sede}"
            )
            return conexion
        except mysql.connector.Error as e:
            print(f"[ERROR] No se pudo conectar a la BD: {e}")
            return None
    
    def test_conexion(self):
        """Prueba la conexión a ambas sedes"""
        print("\n" + "="*60)
        print("TEST 1: Conexión a Base de Datos")
        print("="*60)
        
        for sede in [1, 2]:
            print(f"\nProbando Sede {sede}...")
            conexion = self.conectar(sede)
            
            if conexion:
                print(f"  ✓ Conexión exitosa a biblioteca_sede{sede}")
                conexion.close()
            else:
                print(f"  ✗ Fallo en conexión a biblioteca_sede{sede}")
                return False
        
        return True
    
    def test_datos_iniciales(self):
        """Verifica que los datos iniciales estén cargados"""
        print("\n" + "="*60)
        print("TEST 2: Datos Iniciales")
        print("="*60)
        
        for sede in [1, 2]:
            print(f"\nSede {sede}:")
            conexion = self.conectar(sede)
            
            if not conexion:
                print(f"  ✗ No se pudo conectar")
                continue
            
            cursor = conexion.cursor()
            
            # Verificar libros
            cursor.execute("SELECT COUNT(*) FROM libros")
            total_libros = cursor.fetchone()[0]
            print(f"  → Libros registrados: {total_libros}")
            
            if total_libros < 1000:
                print(f"  ⚠ Advertencia: Se esperaban 1000 libros")
            else:
                print(f"  ✓ Cantidad correcta de libros")
            
            # Verificar préstamos
            cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'ACTIVO'")
            prestamos = cursor.fetchone()[0]
            print(f"  → Préstamos activos: {prestamos}")
            
            esperado = 50 if sede == 1 else 150
            if prestamos == esperado:
                print(f"  ✓ Cantidad correcta de préstamos")
            else:
                print(f"  ⚠ Se esperaban {esperado} préstamos")
            
            # Verificar ejemplares disponibles
            cursor.execute("SELECT SUM(ejemplares_disponibles) FROM libros")
            disponibles = cursor.fetchone()[0]
            print(f"  → Ejemplares disponibles: {disponibles}")
            
            cursor.close()
            conexion.close()
    
    def test_operaciones_bd(self):
        """Prueba operaciones básicas en la BD"""
        print("\n" + "="*60)
        print("TEST 3: Operaciones en Base de Datos")
        print("="*60)
        
        sede = 1
        conexion = self.conectar(sede)
        
        if not conexion:
            print("  ✗ No se pudo conectar a la BD")
            return
        
        cursor = conexion.cursor()
        
        # Test 3: Verificar tablas
        print("\n3. Verificar estructura de tablas...")
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()
        print(f"  ✓ Tablas encontradas: {', '.join([t[0] for t in tablas])}")
        
        cursor.close()
        conexion.close()
    
    def mostrar_estado_sistema(self):
        """Muestra un resumen del estado actual del sistema"""
        print("\n" + "="*60)
        print("ESTADO ACTUAL DEL SISTEMA")
        print("="*60)
        
        for sede in [1, 2]:
            conexion = self.conectar(sede)
            if not conexion:
                continue
            
            cursor = conexion.cursor()
            
            print(f"\n📍 SEDE {sede}")
            print("-" * 40)
            
            # Resumen de libros
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(ejemplares_totales) as ejemplares_totales,
                    SUM(ejemplares_disponibles) as ejemplares_disponibles
                FROM libros
            """)
            stats = cursor.fetchone()
            print(f"Libros únicos: {stats[0]}")
            print(f"Ejemplares totales: {stats[1]}")
            print(f"Ejemplares disponibles: {stats[2]}")
            print(f"Ejemplares prestados: {stats[1] - stats[2]}")
            
            # Préstamos por estado
            cursor.execute("""
                SELECT estado, COUNT(*) 
                FROM prestamos 
                GROUP BY estado
            """)
            print(f"\nPréstamos:")
            for estado, cantidad in cursor.fetchall():
                print(f"  - {estado}: {cantidad}")
            
            # Operaciones recientes
            cursor.execute("""
                SELECT operacion, COUNT(*) 
                FROM historial_operaciones 
                GROUP BY operacion
            """)
            operaciones = cursor.fetchall()
            if operaciones:
                print(f"\nHistorial de operaciones:")
                for op, cantidad in operaciones:
                    print(f"  - {op}: {cantidad}")
            
            # Últimas operaciones
            cursor.execute("""
                SELECT operacion, codigo_libro, usuario_id, fecha
                FROM historial_operaciones 
                ORDER BY fecha DESC 
                LIMIT 5
            """)
            ultimas = cursor.fetchall()
            if ultimas:
                print(f"\nÚltimas 5 operaciones:")
                for i, (op, libro, usuario, fecha) in enumerate(ultimas, 1):
                    print(f"  {i}. {op} | Libro: {libro} | Usuario: {usuario} | {fecha}")
            
            cursor.close()
            conexion.close()
    
    def ejecutar_todos(self):
        """Ejecuta todos los tests"""
        print("\n" + "█"*60)
        print("  SISTEMA DE PRUEBAS - BIBLIOTECA DISTRIBUIDA")
        print("█"*60)
        print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Host BD: {self.host}:{self.port}")
        
        try:
            # Test 1: Conexión
            if not self.test_conexion():
                print("\n❌ Tests detenidos: Fallo en conexión")
                return False
            
            # Test 2: Datos iniciales
            self.test_datos_iniciales()
            
            # Test 3: Operaciones BD
            self.test_operaciones_bd()
            
            # Mostrar estado
            self.mostrar_estado_sistema()
            
            print("\n" + "="*60)
            print("✅ TODOS LOS TESTS COMPLETADOS")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR durante los tests: {e}")
            return False


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Uso: python test_sistema.py [host] [puerto]")
        print("\nEjemplo:")
        print("  python test_sistema.py localhost 3306")
        print("\nOpciones:")
        print("  -h, --help    Muestra esta ayuda")
        sys.exit(0)
    
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 3306
    
    tester = TestSistema(host, port)
    
    try:
        exito = tester.ejecutar_todos()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrumpidos por el usuario")
        sys.exit(1)


if __name__ == "__main__":
    main()
 1: Buscar un libro
        print("\n1. Buscar libro por código...")
        cursor.execute("SELECT codigo, nombre, ejemplares_disponibles FROM libros WHERE codigo = 'LIB00001'")
        libro = cursor.fetchone()
        
        if libro:
            print(f"  ✓ Libro encontrado:")
            print(f"    Código: {libro[0]}")
            print(f"    Nombre: {libro[1]}")
            print(f"    Disponibles: {libro[2]}")
        else:
            print("  ✗ Libro no encontrado")
        
        # Test 2: Consultar préstamos activos
        print("\n2. Consultar préstamos activos...")
        cursor.execute("""
            SELECT p.codigo_libro, l.nombre, p.usuario_id, p.fecha_entrega
            FROM prestamos p
            JOIN libros l ON p.codigo_libro = l.codigo
            WHERE p.estado = 'ACTIVO'
            LIMIT 5
        """)
        
        prestamos = cursor.fetchall()
        print(f"  ✓ {len(prestamos)} préstamos encontrados (mostrando primeros 5):")
        for i, p in enumerate(prestamos, 1):
            print(f"    {i}. Libro: {p[1][:40]} | Usuario: {p[2]} | Entrega: {p[3]}")
        
        # Test