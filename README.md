# Sistema Distribuido de Préstamo de Libros - Primera Entrega

Sistema distribuido para el préstamo de libros en la Universidad Ada Lovelace. Implementa operaciones de devolución y renovación de libros utilizando patrones de comunicación asíncronos (Pub/Sub) con ZeroMQ y MySQL como base de datos.

## 📋 Requisitos

- Python 3.8 o superior
- MySQL 8.0
- Docker y Docker Compose (opcional, para contenedor MySQL)

Puedes usar el template de AWS CloudFormation para crear la infraestructura necesaria para ejecutar este proyecto en la nube ☁️.
Los templates disponibles en el momento son:
- Primera entrega: template-proyecto.yaml

## 🚀 Instalación

### 1. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 2. Configurar Base de Datos

#### Opción A: Usar Docker (Recomendado)

```bash
# Iniciar contenedor MySQL
docker-compose up -d

# Esperar a que MySQL esté listo (unos 30 segundos)
docker-compose logs -f mysql
```

#### Opción B: MySQL local

Si tienes MySQL instalado localmente, ejecuta el script SQL:

```bash
mysql -u root -p < setup_database.sql
```
o al contenedor del docker-compose

```bash
docker exec -it biblioteca_mysql mysql -u root -prootpass < setup_database.sql

```


### 3. Generar datos iniciales

```bash
# Si usas Docker
python3.12 generar_datos_inic.py localhost 3306

# Si MySQL está en otro host
python3.12 generar_datos_inic.py <host> <puerto>
```

Esto creará:
- 1000 libros en ambas sedes
- 50 préstamos activos en Sede 1
- 150 préstamos activos en Sede 2

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐
│ Proceso         │
│ Solicitante (PS)│
└────────┬────────┘
         │ REQ/REP (ZeroMQ)
         ▼
┌─────────────────┐
│ Gestor de       │
│ Carga (GC)      │
└────────┬────────┘
         │ PUB/SUB (ZeroMQ)
         ▼
┌─────────────────┐        ┌──────────┐
│ Actores         │───────▶│  MySQL   │
│ (Devolución/    │        │  Sede 1  │
│  Renovación)    │        └──────────┘
└─────────────────┘
```

## 🎮 Ejecución

### Configuración para 2 computadoras (mínimo requerido)

#### **Computadora 1: Gestor de Carga + Actores (Sede 1)**

```bash
# Terminal 1: Gestor de Carga
python3.12 gestor_carga.py 1 5555 5556

# Terminal 2: Actor Devolución
python3.12 actor.py DEVOLUCION 1 localhost 5556 <mysql_host> 3306

# Terminal 3: Actor Renovación
python3.12 actor.py RENOVACION 1 localhost 5556 <mysql_host> 3306
```

también puedes correrlos como servicios usando nohup. De este modo los ejecutas en segundo plano, y almacenas su logs en los archivos .log

```bash
nohup python3.12 gestor_carga.py 1 5555 5556 > gestor.log 2>&1 &

nohup python3.12 actor.py DEVOLUCION 1 localhost 5556 localhost 3306 > devolucion.log 2>&1 &

nohup python3.12 actor.py RENOVACION 1 localhost 5556 localhost 3306 > renovacion.log 2>&1 &

```


#### **Computadora 2: Proceso Solicitante**

```bash
# Ejecutar PS conectándose al GC de la Computadora 1
python3.12 proceso_solicitante.py peticiones.txt <ip_computadora_1> 5555
```

### Configuración completa para 3 computadoras

#### **Computadora 1: GC + Actores Sede 1**

```bash
# Terminal 1: Gestor de Carga Sede 1
python3.12 gestor_cargar.py 1 5555 5556

# Terminal 2: Actor Devolución Sede 1
python3.12 actor.py DEVOLUCION 1 localhost 5556 <mysql_host> 3306

# Terminal 3: Actor Renovación Sede 1
python3.12 actor.py RENOVACION 1 localhost 5556 <mysql_host> 3306
```

#### **Computadora 2: GC + Actores Sede 2**

```bash
# Terminal 1: Gestor de Carga Sede 2
python3.12 gestor_cargar.py 2 5557 5558

# Terminal 2: Actor Devolución Sede 2
python3.12 actor.py DEVOLUCION 2 localhost 5558 <mysql_host> 3306

# Terminal 3: Actor Renovación Sede 2
python3.12 actor.py RENOVACION 2 localhost 5558 <mysql_host> 3306
```

#### **Computadora 3: Procesos Solicitantes**

```bash
# PS para Sede 1
python3.12 proceso_solicitante.py peticiones.txt <ip_comp1> 5555

# PS para Sede 2 (en otra terminal)
python3.12 proceso_solicitante.py peticiones.txt <ip_comp2> 5557
```

## 📝 Formato del Archivo de Peticiones

El archivo de peticiones debe tener el siguiente formato (mínimo 20 líneas):

```
OPERACION|CODIGO_LIBRO|USUARIO_ID
```

Ejemplo:
```
DEVOLUCION|LIB00001|USR1001
RENOVACION|LIB00025|USR2002
PRESTAMO|LIB00300|USR3001
```

## 🔍 Verificar el Sistema

### Ver estado de la Base de Datos

```bash
# Conectarse a MySQL
docker exec -it biblioteca_mysql mysql -u root -prootpass

# Ver libros disponibles en Sede 1
USE biblioteca_sede1;
SELECT codigo, nombre, ejemplares_disponibles FROM libros LIMIT 10;

# Ver préstamos activos
SELECT * FROM prestamos WHERE estado = 'ACTIVO' LIMIT 10;

# Ver historial de operaciones
SELECT * FROM historial_operaciones ORDER BY fecha DESC LIMIT 10;
```

### Observar operaciones en tiempo real

Los procesos muestran mensajes en consola indicando:
- **PS**: Peticiones enviadas y respuestas recibidas
- **GC**: Peticiones procesadas y tópicos publicados
- **Actores**: Mensajes recibidos y actualizaciones a la BD

## 🎯 Funcionalidades Implementadas (Primera Entrega)

✅ **Proceso Solicitante (PS)**
- Lectura de peticiones desde archivo
- Envío de peticiones al Gestor de Carga
- Comunicación REQ/REP con ZeroMQ

✅ **Gestor de Carga (GC)**
- Recepción de peticiones de PS
- Respuesta inmediata para devoluciones y renovaciones
- Publicación de tópicos para Actores

✅ **Actores**
- Suscripción a tópicos DEVOLUCION y RENOVACION
- Actualización de BD al recibir mensajes
- Registro de operaciones en historial

✅ **Base de Datos**
- 1000 libros iniciales
- 200 préstamos activos distribuidos
- Persistencia en MySQL
- Tablas de libros, préstamos e historial

✅ **Distribución**
- Ejecución en mínimo 2 computadoras
- Comunicación entre procesos con ZeroMQ

## 📊 Estructura de Tablas

### libros
- `codigo`: Identificador único del libro
- `nombre`: Título del libro
- `autor`: Autor
- `ejemplares_totales`: Total de ejemplares
- `ejemplares_disponibles`: Ejemplares disponibles para préstamo

### prestamos
- `codigo_libro`: Libro prestado
- `usuario_id`: Usuario que tiene el préstamo
- `fecha_prestamo`, `fecha_entrega`: Fechas del préstamo
- `renovaciones`: Número de renovaciones (máximo 2)
- `estado`: ACTIVO, DEVUELTO, VENCIDO

### historial_operaciones
- Registro de todas las operaciones realizadas
- Incluye DEVOLUCION, RENOVACION, PRESTAMO

## 🐛 Solución de Problemas

### Error de conexión a MySQL
```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Ver logs de MySQL
docker-compose logs mysql
```

### Error "Address already in use"
```bash
# Cambiar los puertos en los comandos de ejecución
# GC: usar puerto diferente a 5555
# Actor: conectarse al nuevo puerto del GC
```

### Los Actores no reciben mensajes
- Verificar que el GC se inició antes que los Actores
- Confirmar que los puertos coinciden
- Dar unos segundos para que la suscripción se establezca

## 📦 Archivos del Proyecto

```
proyecto/
├── proceso_solicitante.py    # Proceso Solicitante
├── gestor_carga.py           # Gestor de Carga
├── actor.py                  # Actor (Devolución/Renovación)
├── generar_datos_iniciales.py # Script de datos iniciales
├── setup_database.sql        # Script de BD
├── peticiones.txt            # Archivo de ejemplo
├── docker-compose.yml        # Configuración Docker
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

## 👥 Equipo de Desarrollo

Samuel Emperador
Alejandro Barragan

## 📅 Fechas

- **Primera Entrega**: 7 de octubre, 2025

---

**Pontifica Universidad Javeriana**  
*Introducción a Sistemas Distribuidos 2025-30*
