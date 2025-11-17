# Sistema Distribuido de Préstamo de Libros - Segunda Entrega

Sistema distribuido para el préstamo de libros en la Universidad Ada Lovelace. Implementa operaciones de devolución, renovación y préstamo utilizando:
- **Patrones asíncronos (Pub/Sub)** para devoluciones y renovaciones
- **Patrón síncrono (REQ/REP)** para préstamos
- **Gestor de Almacenamiento (GA)** como intermediario con la base de datos

## 📋 Requisitos

- Python 3.8 o superior
- MySQL 8.0
- Docker y Docker Compose (opcional, para contenedor MySQL)
- ZeroMQ

## 🏗️ Arquitectura Actualizada

```
┌─────────────────┐
│ Proceso         │
│ Solicitante (PS)│
└────────┬────────┘
         │ REQ/REP
         ▼
┌─────────────────┐         ┌──────────────┐
│ Gestor de       │────────▶│ Actor        │
│ Carga (GC)      │ PUB/SUB │ Devolución   │
│                 │         └──────┬───────┘
│                 │         ┌──────▼───────┐        ┌──────────────┐
│                 │────────▶│ Actor        │───────▶│ Gestor       │
│                 │ PUB/SUB │ Renovación   │ REQ/REP│ Almacenamiento│
│                 │         └──────────────┘        │ (GA)         │
│                 │         ┌──────────────┐        │              │
│                 │────────▶│ Actor        │───────▶│              │
│                 │ REQ/REP │ Préstamo     │ REQ/REP└──────┬───────┘
└─────────────────┘         └──────────────┘               │
                                                            ▼
                                                     ┌──────────────┐
                                                     │   MySQL      │
                                                     │ BD Principal │
                                                     └──────┬───────┘
                                                            │
                                                            ▼
                                                     ┌──────────────┐
                                                     │   MySQL      │
                                                     │  BD Réplica  │
                                                     └──────────────┘
```

## 🆕 Cambios Principales

### Nueva Arquitectura con Gestor de Almacenamiento

1. **Gestor de Almacenamiento (GA)**: 
   - Maneja todas las conexiones a la base de datos
   - Proporciona interfaz REQ/REP para operaciones de BD
   - Implementa pool de conexiones y health checks
   - Soporta failover automático a BD réplica

2. **Actores Refactorizados**:
   - Ya NO se conectan directamente a la BD
   - Envían solicitudes al GA mediante REQ/REP
   - Mantienen su comportamiento asíncrono (SUB) o síncrono (REP)

3. **Operaciones Soportadas**:
   - ✅ **DEVOLUCION**: Asíncrona (PUB/SUB)
   - ✅ **RENOVACION**: Asíncrona (PUB/SUB)
   - ✅ **PRESTAMO**: Síncrona (REQ/REP) con transacción ACID

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

### 3. Generar datos iniciales

```bash
python3.12 generar_datos_inic.py localhost 3306
```

## 🎮 Ejecución del Sistema Completo

### Orden de Inicio de Componentes

Para el correcto funcionamiento, los componentes deben iniciarse en este orden:

1. **Gestor de Almacenamiento (GA)**
2. **Actores** (Devolución, Renovación, Préstamo)
3. **Gestor de Carga (GC)**
4. **Proceso Solicitante (PS)**

### Configuración para 2 computadoras (mínimo)

#### **Computadora 1: Infraestructura Backend (GA + GC + Actores)**

```bash
# Terminal 1: Gestor de Almacenamiento
python3.12 gestor_almacenamiento.py 1 5560 localhost 3306

# Terminal 2: Actor Devolución
python3.12 actor.py DEVOLUCION 1 localhost 5556 localhost 5560

# Terminal 3: Actor Renovación
python3.12 actor.py RENOVACION 1 localhost 5556 localhost 5560

# Terminal 4: Actor Préstamo
python3.12 actor.py PRESTAMO 1 localhost 5556 localhost 5560 5559

# Terminal 5: Gestor de Carga
python3.12 gestor_carga.py 1 5555 5556 5559
```

**Usando nohup (ejecución en segundo plano):**

```bash
# Gestor de Almacenamiento
nohup python3.12 gestor_almacenamiento.py 1 5560 localhost 3306 > ga.log 2>&1 &

# Actores
nohup python3.12 actor.py DEVOLUCION 1 localhost 5556 localhost 5560 > devolucion.log 2>&1 &
nohup python3.12 actor.py RENOVACION 1 localhost 5556 localhost 5560 > renovacion.log 2>&1 &
nohup python3.12 actor.py PRESTAMO 1 localhost 5556 localhost 5560 5559 > prestamo.log 2>&1 &

# Gestor de Carga
nohup python3.12 gestor_carga.py 1 5555 5556 5559 > gestor.log 2>&1 &
```

#### **Computadora 2: Proceso Solicitante**

```bash
# Ejecutar PS conectándose al GC de la Computadora 1
python3.12 proceso_solicitante.py peticiones.txt <ip_computadora_1> 5555
```

### Configuración completa para 3 computadoras

#### **Computadora 1: Sede 1**

```bash
# GA Sede 1
nohup python3.12 gestor_almacenamiento.py 1 5560 <mysql_host> 3306 > ga1.log 2>&1 &

# Actores Sede 1
nohup python3.12 actor.py DEVOLUCION 1 localhost 5556 localhost 5560 > dev1.log 2>&1 &
nohup python3.12 actor.py RENOVACION 1 localhost 5556 localhost 5560 > ren1.log 2>&1 &
nohup python3.12 actor.py PRESTAMO 1 localhost 5556 localhost 5560 5559 > prest1.log 2>&1 &

# GC Sede 1
nohup python3.12 gestor_carga.py 1 5555 5556 5559 > gc1.log 2>&1 &
```

#### **Computadora 2: Sede 2**

```bash
# GA Sede 2
nohup python3.12 gestor_almacenamiento.py 2 5561 <mysql_host> 3306 > ga2.log 2>&1 &

# Actores Sede 2
nohup python3.12 actor.py DEVOLUCION 2 localhost 5558 localhost 5561 > dev2.log 2>&1 &
nohup python3.12 actor.py RENOVACION 2 localhost 5558 localhost 5561 > ren2.log 2>&1 &
nohup python3.12 actor.py PRESTAMO 2 localhost 5558 localhost 5561 5560 > prest2.log 2>&1 &

# GC Sede 2
nohup python3.12 gestor_carga.py 2 5557 5558 5560 > gc2.log 2>&1 &
```

#### **Computadora 3: Procesos Solicitantes**

```bash
# PS para Sede 1
python3.12 proceso_solicitante.py peticiones_sede1.txt <ip_comp1> 5555

# PS para Sede 2 (en otra terminal)
python3.12 proceso_solicitante.py peticiones_sede2.txt <ip_comp2> 5557
```

## 📝 Formato del Archivo de Peticiones

```
OPERACION|CODIGO_LIBRO|USUARIO_ID
```

Ejemplo (ver `peticiones.txt`):
```
DEVOLUCION|LIB00001|USR1001
RENOVACION|LIB00025|USR2002
PRESTAMO|LIB00300|USR3001
```

## 🔍 Puertos Utilizados

### Sede 1
- **5555**: GC recibe de PS (REP)
- **5556**: GC publica a actores (PUB)
- **5559**: Actor Préstamo (REP)
- **5560**: Gestor Almacenamiento (REP)
- **3306**: MySQL

### Sede 2
- **5557**: GC recibe de PS (REP)
- **5558**: GC publica a actores (PUB)
- **5560**: Actor Préstamo (REP)
- **5561**: Gestor Almacenamiento (REP)
- **3306**: MySQL

## 🔄 Flujo de Operaciones

### Devolución (Asíncrona ~3ms)
```
PS → GC (REQ/REP) → Actor Dev (PUB/SUB) → GA (REQ/REP) → BD
     ↓ inmediata
     OK al PS
```

### Renovación (Asíncrona ~3ms)
```
PS → GC (REQ/REP) → Actor Ren (PUB/SUB) → GA (REQ/REP) → BD
     ↓ inmediata
     OK + nueva_fecha al PS
```

### Préstamo (Síncrona ~80ms)
```
PS → GC (REQ/REP) → Actor Prest (REQ/REP) → GA (REQ/REP) → BD
                                           ↓ SELECT
                                           ↓ TRANSACTION
                                           ↓ UPDATE + INSERT
     ↓ espera BD
     OK + fecha_entrega al PS
```

## 🧪 Verificar el Sistema

### Monitorear Logs

```bash
# Ver logs de todos los componentes
tail -f *.log

# Ver log específico
tail -f ga.log
tail -f devolucion.log
```

### Verificar Base de Datos

```bash
# Conectarse a MySQL
docker exec -it biblioteca_mysql mysql -u root -prootpass

# Ver libros disponibles
USE biblioteca_sede1;
SELECT codigo, nombre, ejemplares_disponibles FROM libros LIMIT 10;

# Ver préstamos activos
SELECT * FROM prestamos WHERE estado = 'ACTIVO' LIMIT 10;

# Ver historial reciente
SELECT * FROM historial_operaciones ORDER BY fecha DESC LIMIT 10;
```

### Detener Procesos en Segundo Plano

```bash
# Ver procesos Python corriendo
ps aux | grep python

# Matar un proceso específico
kill <PID>

# Matar todos los procesos Python del proyecto
pkill -f "gestor_almacenamiento.py"
pkill -f "actor.py"
pkill -f "gestor_carga.py"
```

## 🎯 Funcionalidades Implementadas

### ✅ Primera Entrega
- Proceso Solicitante (PS)
- Gestor de Carga (GC) con PUB/SUB
- Actores Devolución y Renovación (asíncronos)
- Base de datos con 1000 libros
- Comunicación distribuida ZeroMQ

### ✅ Segunda Entrega
- **Gestor de Almacenamiento (GA)** como intermediario de BD
- **Actor de Préstamo** con operación síncrona
- **Transacciones ACID** para préstamos
- **Pool de conexiones** a BD
- **Health checks** y preparación para failover
- **Replicación asíncrona** simulada

## 📊 Operaciones del Gestor de Almacenamiento

El GA soporta las siguientes operaciones:

1. **UPDATE_DEVOLUCION**: Incrementa ejemplares disponibles
2. **UPDATE_RENOVACION**: Actualiza fecha de entrega
3. **INSERT_HISTORIAL**: Registra operaciones
4. **SELECT_DISPONIBILIDAD**: Consulta disponibilidad de libros
5. **TRANSACCION_PRESTAMO**: Transacción ACID completa para préstamos

## 🐛 Solución de Problemas

### Error: "Address already in use"
```bash
# Cambiar los puertos o matar el proceso que los usa
lsof -ti:5560 | xargs kill -9
```

### Actores no reciben mensajes
- Verificar que el GA se inició antes que los Actores
- Verificar que el GC se inició después de los Actores
- Confirmar que los puertos coinciden
- Dar unos segundos para establecer conexiones

### Error de conexión a MySQL
```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Ver logs de MySQL
docker-compose logs mysql

# Reiniciar contenedor
docker-compose restart mysql
```

### El GA no responde
- Verificar logs: `tail -f ga.log`
- Verificar que MySQL esté disponible
- Reiniciar el GA

## 📦 Archivos Principales

```
proyecto/
├── proceso_solicitante.py         # Proceso Solicitante (PS)
├── gestor_carga.py                # Gestor de Carga (GC) ✨ ACTUALIZADO
├── actor.py                       # Actores ✨ REFACTORIZADO
├── gestor_almacenamiento.py       # Gestor de Almacenamiento ✨ NUEVO
├── generar_datos_iniciales.py     # Script de datos iniciales
├── setup_database.sql             # Script de BD
├── peticiones.txt                 # Archivo de ejemplo
├── docker-compose.yml             # Configuración Docker
├── requirements.txt               # Dependencias Python
└── README.md                      # Este archivo
```

## 👥 Equipo de Desarrollo

Samuel Emperador  
Alejandro Barragan

## 📅 Fechas

- **Primera Entrega**: 7 de octubre, 2025
- **Segunda Entrega**: 18 Noviembre, 2025

---

**Pontificia Universidad Javeriana**  
*Introducción a Sistemas Distribuidos 2025-30*