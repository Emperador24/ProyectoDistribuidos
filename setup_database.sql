-- Script de inicialización de la base de datos
-- Sistema de Préstamo de Libros - Universidad Ada Lovelace
-- MySQL 8.x

-- ============================================================================
-- Configuración general
-- ============================================================================
SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ============================================================================
-- Crear bases de datos de las dos sedes
-- ============================================================================
CREATE DATABASE IF NOT EXISTS biblioteca_sede1 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS biblioteca_sede2 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- ============================================================================
-- Usuario de aplicación
-- ============================================================================
CREATE USER IF NOT EXISTS 'biblioteca_user'@'%' IDENTIFIED BY 'biblioteca_pass';
GRANT ALL PRIVILEGES ON biblioteca_sede1.* TO 'biblioteca_user'@'%';
GRANT ALL PRIVILEGES ON biblioteca_sede2.* TO 'biblioteca_user'@'%';
FLUSH PRIVILEGES;

-- ============================================================================
-- ESQUEMA SEDE 1
-- ============================================================================
USE biblioteca_sede1;

-- Tabla de libros
CREATE TABLE IF NOT EXISTS libros (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    codigo                    VARCHAR(20)  NOT NULL UNIQUE,
    nombre                    VARCHAR(255) NOT NULL,
    autor                     VARCHAR(255),
    editorial                 VARCHAR(100),
    isbn                      VARCHAR(20),
    ejemplares_totales        INT NOT NULL DEFAULT 1 CHECK (ejemplares_totales >= 0),
    ejemplares_disponibles    INT NOT NULL DEFAULT 1 CHECK (ejemplares_disponibles >= 0),
    fecha_registro            DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_codigo (codigo),
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de préstamos
CREATE TABLE IF NOT EXISTS prestamos (
    id                         INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro               VARCHAR(20) NOT NULL,
    usuario_id                 VARCHAR(50) NOT NULL,
    fecha_prestamo             DATETIME NOT NULL,
    fecha_entrega              DATETIME NOT NULL,
    fecha_devolucion_real      DATETIME NULL,
    renovaciones               INT DEFAULT 0 CHECK (renovaciones >= 0),
    estado                     ENUM('ACTIVO','DEVUELTO','VENCIDO') NOT NULL DEFAULT 'ACTIVO',
    sede                       INT NOT NULL,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_prestamos_libro
        FOREIGN KEY (codigo_libro) REFERENCES libros(codigo)
        ON UPDATE CASCADE,
    INDEX idx_usuario (usuario_id),
    INDEX idx_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de historial de operaciones
CREATE TABLE IF NOT EXISTS historial_operaciones (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro  VARCHAR(20) NOT NULL,
    usuario_id    VARCHAR(50) NOT NULL,
    operacion     ENUM('PRESTAMO','DEVOLUCION','RENOVACION') NOT NULL,
    fecha         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sede          INT NOT NULL,
    datos_adicionales TEXT NULL,
    INDEX idx_fecha (fecha),
    INDEX idx_operacion (operacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- ESQUEMA SEDE 2 (idéntico al de la sede 1)
-- ============================================================================
USE biblioteca_sede2;

-- Tabla de libros
CREATE TABLE IF NOT EXISTS libros (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    codigo                    VARCHAR(20)  NOT NULL UNIQUE,
    nombre                    VARCHAR(255) NOT NULL,
    autor                     VARCHAR(255),
    editorial                 VARCHAR(100),
    isbn                      VARCHAR(20),
    ejemplares_totales        INT NOT NULL DEFAULT 1 CHECK (ejemplares_totales >= 0),
    ejemplares_disponibles    INT NOT NULL DEFAULT 1 CHECK (ejemplares_disponibles >= 0),
    fecha_registro            DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_codigo (codigo),
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de préstamos
CREATE TABLE IF NOT EXISTS prestamos (
    id                         INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro               VARCHAR(20) NOT NULL,
    usuario_id                 VARCHAR(50) NOT NULL,
    fecha_prestamo             DATETIME NOT NULL,
    fecha_entrega              DATETIME NOT NULL,
    fecha_devolucion_real      DATETIME NULL,
    renovaciones               INT DEFAULT 0 CHECK (renovaciones >= 0),
    estado                     ENUM('ACTIVO','DEVUELTO','VENCIDO') NOT NULL DEFAULT 'ACTIVO',
    sede                       INT NOT NULL,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_prestamos_libro_s2
        FOREIGN KEY (codigo_libro) REFERENCES libros(codigo)
        ON UPDATE CASCADE,
    INDEX idx_usuario (usuario_id),
    INDEX idx_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de historial de operaciones
CREATE TABLE IF NOT EXISTS historial_operaciones (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro  VARCHAR(20) NOT NULL,
    usuario_id    VARCHAR(50) NOT NULL,
    operacion     ENUM('PRESTAMO','DEVOLUCION','RENOVACION') NOT NULL,
    fecha         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sede          INT NOT NULL,
    datos_adicionales TEXT NULL,
    INDEX idx_fecha (fecha),
    INDEX idx_operacion (operacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Fin del script