#!/bin/bash
# Script para ejecutar el sistema distribuido completo
# Universidad Ada Lovelace - Sistema de Préstamo de Libros

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Sistema Distribuido de Préstamo de Libros"
echo "Universidad Ada Lovelace"
echo "=========================================="
echo ""

# Función para mostrar ayuda
mostrar_ayuda() {
    echo "Uso: ./ejecutar_sistema.sh [opcion]"
    echo ""
    echo "Opciones:"
    echo "  setup       - Configurar BD y generar datos iniciales"
    echo "  sede1       - Iniciar Gestor y Actores Sede 1"
    echo "  sede2       - Iniciar Gestor y Actores Sede 2"
    echo "  ps          - Iniciar Proceso Solicitante"
    echo "  test        - Ejecutar tests del sistema"
    echo "  clean       - Limpiar contenedores Docker"
    echo "  help        - Mostrar esta ayuda"
    echo ""
    echo "Ejemplo de uso:"
    echo "  ./ejecutar_sistema.sh setup    # Primero configurar"
    echo "  ./ejecutar_sistema.sh sede1    # En computadora 1"
    echo "  ./ejecutar_sistema.sh ps       # En computadora 2"
}

# Función para setup inicial
setup() {
    echo -e "${BLUE}[SETUP]${NC} Iniciando configuración del sistema..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}[ERROR]${NC} Docker no está instalado"
        exit 1
    fi
    
    # Iniciar contenedor MySQL
    echo -e "${BLUE}[SETUP]${NC} Iniciando contenedor MySQL..."
    docker-compose up -d
    
    echo -e "${YELLOW}[SETUP]${NC} Esperando a que MySQL esté listo (30 segundos)..."
    sleep 30
    
    # Verificar conexión
    echo -e "${BLUE}[SETUP]${NC} Verificando conexión a BD..."
    python3 test_sistema.py localhost 3306 > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SETUP]${NC} ✓ MySQL está listo"
    else
        echo -e "${YELLOW}[SETUP]${NC} Esperando 15 segundos más..."
        sleep 15
    fi
    
    # Generar datos iniciales
    echo -e "${BLUE}[SETUP]${NC} Generando datos iniciales..."
    python3 generar_datos_iniciales.py localhost 3306
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SETUP]${NC} ✓ Sistema configurado correctamente"
        echo ""
        echo "Siguientes pasos:"
        echo "  1. En computadora 1: ./ejecutar_sistema.sh sede1"
        echo "  2. En computadora 2: ./ejecutar_sistema.sh ps"
    else
        echo -e "${RED}[ERROR]${NC} Falló la generación de datos"
        exit 1
    fi
}

# Función para iniciar Sede 1
sede1() {
    echo -e "${BLUE}[SEDE1]${NC} Iniciando Gestor de Carga y Actores..."
    
    # Verificar host de MySQL
    read -p "Host de MySQL [localhost]: " MYSQL_HOST
    MYSQL_HOST=${MYSQL_HOST:-localhost}
    
    echo ""
    echo -e "${GREEN}[SEDE1]${NC} Iniciando componentes..."
    echo "Presiona Ctrl+C para detener todos los procesos"
    echo ""
    
    # Función para manejar Ctrl+C
    trap 'echo -e "\n${YELLOW}[SEDE1]${NC} Deteniendo todos los procesos..."; kill 0' SIGINT
    
    # Iniciar Gestor de Carga
    echo -e "${BLUE}[SEDE1]${NC} → Gestor de Carga (puerto 5555/5556)"
    python3 gestor_carga.py 1 5555 5556 &
    
    sleep 2
    
    # Iniciar Actor Devolución
    echo -e "${BLUE}[SEDE1]${NC} → Actor DEVOLUCIÓN"
    python3 actor.py DEVOLUCION 1 localhost 5556 $MYSQL_HOST 3306 &
    
    sleep 1
    
    # Iniciar Actor Renovación
    echo -e "${BLUE}[SEDE1]${NC} → Actor RENOVACIÓN"
    python3 actor.py RENOVACION 1 localhost 5556 $MYSQL_HOST 3306 &
    
    echo ""
    echo -e "${GREEN}[SEDE1]${NC} ✓ Todos los componentes iniciados"
    echo ""
    
    # Esperar
    wait
}

# Función para iniciar Sede 2
sede2() {
    echo -e "${BLUE}[SEDE2]${NC} Iniciando Gestor de Carga y Actores..."
    
    # Verificar host de MySQL
    read -p "Host de MySQL [localhost]: " MYSQL_HOST
    MYSQL_HOST=${MYSQL_HOST:-localhost}
    
    echo ""
    echo -e "${GREEN}[SEDE2]${NC} Iniciando componentes..."
    echo "Presiona Ctrl+C para detener todos los procesos"
    echo ""
    
    # Función para manejar Ctrl+C
    trap 'echo -e "\n${YELLOW}[SEDE2]${NC} Deteniendo todos los procesos..."; kill 0' SIGINT
    
    # Iniciar Gestor de Carga
    echo -e "${BLUE}[SEDE2]${NC} → Gestor de Carga (puerto 5557/5558)"
    python3 gestor_carga.py 2 5557 5558 &
    
    sleep 2
    
    # Iniciar Actor Devolución
    echo -e "${BLUE}[SEDE2]${NC} → Actor DEVOLUCIÓN"
    python3 actor.py DEVOLUCION 2 localhost 5558 $MYSQL_HOST 3306 &
    
    sleep 1
    
    # Iniciar Actor Renovación
    echo -e "${BLUE}[SEDE2]${NC} → Actor RENOVACIÓN"
    python3 actor.py RENOVACION 2 localhost 5558 $MYSQL_HOST 3306 &
    
    echo ""
    echo -e "${GREEN}[SEDE2]${NC} ✓ Todos los componentes iniciados"
    echo ""
    
    # Esperar
    wait
}

# Función para iniciar Proceso Solicitante
ps() {
    echo -e "${BLUE}[PS]${NC} Proceso Solicitante"
    echo ""
    
    # Seleccionar sede
    read -p "¿A qué sede conectar? [1/2]: " SEDE
    SEDE=${SEDE:-1}
    
    # Host del Gestor de Carga
    read -p "Host del Gestor de Carga [localhost]: " GC_HOST
    GC_HOST=${GC_HOST:-localhost}
    
    # Puerto según sede
    if [ "$SEDE" = "1" ]; then
        GC_PORT=5555
    else
        GC_PORT=5557
    fi
    
    # Archivo de peticiones
    read -p "Archivo de peticiones [peticiones.txt]: " ARCHIVO
    ARCHIVO=${ARCHIVO:-peticiones.txt}
    
    if [ ! -f "$ARCHIVO" ]; then
        echo -e "${RED}[ERROR]${NC} Archivo no encontrado: $ARCHIVO"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}[PS]${NC} Conectando a Sede $SEDE en $GC_HOST:$GC_PORT"
    echo -e "${GREEN}[PS]${NC} Archivo: $ARCHIVO"
    echo ""
    
    python3 proceso_solicitante.py $ARCHIVO $GC_HOST $GC_PORT
}

# Función para ejecutar tests
test() {
    echo -e "${BLUE}[TEST]${NC} Ejecutando tests del sistema..."
    
    read -p "Host de MySQL [localhost]: " MYSQL_HOST
    MYSQL_HOST=${MYSQL_HOST:-localhost}
    
    python3 test_sistema.py $MYSQL_HOST 3306
}

# Función para limpiar
clean() {
    echo -e "${YELLOW}[CLEAN]${NC} Limpiando contenedores Docker..."
    docker-compose down -v
    echo -e "${GREEN}[CLEAN]${NC} ✓ Limpieza completada"
}

# Procesar argumentos
case "${1:-help}" in
    setup)
        setup
        ;;
    sede1)
        sede1
        ;;
    sede2)
        sede2
        ;;
    ps)
        ps
        ;;
    test)
        test
        ;;
    clean)
        clean
        ;;
    help|*)
        mostrar_ayuda
        ;;
esac