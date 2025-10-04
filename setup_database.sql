-- Script de inicialización de la base de datos
-- Sistema de Préstamo de Libros - Universidad Ada Lovelace

-- Crear bases de datos para ambas sedes
CREATE DATABASE IF NOT EXISTS biblioteca_sede1;
CREATE DATABASE IF NOT EXISTS biblioteca_sede2;

-- Crear usuario para la aplicación
CREATE USER IF NOT EXISTS 'biblioteca_user'@'%' IDENTIFIED BY 'biblioteca_pass';
GRANT ALL PRIVILEGES ON biblioteca_sede1.* TO 'biblioteca_user'@'%';
GRANT ALL PRIVILEGES ON biblioteca_sede2.* TO 'biblioteca_user'@'%';
FLUSH PRIVILEGES;

-- ===================================================================
-- SEDE 1
-- ===================================================================
USE biblioteca_sede1;

-- Tabla de libros
CREATE TABLE IF NOT EXISTS libros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    autor VARCHAR(255),
    editorial VARCHAR(100),
    isbn VARCHAR(20),
    ejemplares_totales INT NOT NULL DEFAULT 1,
    ejemplares_disponibles INT NOT NULL DEFAULT 1,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_codigo (codigo),
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de préstamos
CREATE TABLE IF NOT EXISTS prestamos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro VARCHAR(20) NOT NULL,
    usuario_id VARCHAR(50) NOT NULL,
    fecha_prestamo DATETIME NOT NULL,
    fecha_entrega DATETIME NOT NULL,
    fecha_devolucion_real DATETIME NULL,
    renovaciones INT DEFAULT 0,
    estado ENUM('ACTIVO', 'DEVUELTO', 'VENCIDO') DEFAULT 'ACTIVO',
    sede INT NOT NULL,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (codigo_libro) REFERENCES libros(codigo),
    INDEX idx_usuario (usuario_id),
    INDEX idx_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de historial de operaciones
CREATE TABLE IF NOT EXISTS historial_operaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro VARCHAR(20) NOT NULL,
    usuario_id VARCHAR(50) NOT NULL,
    operacion ENUM('PRESTAMO', 'DEVOLUCION', 'RENOVACION') NOT NULL,
    fecha DATETIME NOT NULL,
    sede INT NOT NULL,
    datos_adicionales TEXT,
    INDEX idx_fecha (fecha),
    INDEX idx_operacion (operacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;orial de operaciones
CREATE TABLE IF NOT EXISTS historial_operaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro VARCHAR(20) NOT NULL,
    usuario_id VARCHAR(50) NOT NULL,
    operacion ENUM('PRESTAMO', 'DEVOLUCION', 'RENOVACION') NOT NULL,
    fecha DATETIME NOT NULL,
    sede INT NOT NULL,
    datos_adicionales TEXT,
    INDEX idx_fecha (fecha),
    INDEX idx_operacion (operacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================================================================
-- SEDE 2
-- ===================================================================
USE biblioteca_sede2;

-- Tabla de libros
CREATE TABLE IF NOT EXISTS libros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    autor VARCHAR(255),
    editorial VARCHAR(100),
    isbn VARCHAR(20),
    ejemplares_totales INT NOT NULL DEFAULT 1,
    ejemplares_disponibles INT NOT NULL DEFAULT 1,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_codigo (codigo),
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de préstamos
CREATE TABLE IF NOT EXISTS prestamos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro VARCHAR(20) NOT NULL,
    usuario_id VARCHAR(50) NOT NULL,
    fecha_prestamo DATETIME NOT NULL,
    fecha_entrega DATETIME NOT NULL,
    fecha_devolucion_real DATETIME NULL,
    renovaciones INT DEFAULT 0,
    estado ENUM('ACTIVO', 'DEVUELTO', 'VENCIDO') DEFAULT 'ACTIVO',
    sede INT NOT NULL,
    fecha_ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (codigo_libro) REFERENCES libros(codigo),
    INDEX idx_usuario (usuario_id),
    INDEX idx_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla de historial de operaciones
CREATE TABLE IF NOT EXISTS historial_operaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro VARCHAR(20) NOT NULL,
    usuario_id VARCHAR(50) NOT NULL,
    operacion ENUM('PRESTAMO', 'DEVOLUCION', 'RENOVACION') NOT NULL,
    fecha DATETIME NOT NULL,
    sede INT NOT NULL,
    datos_adicionales TEXT,
    INDEX idx_fecha (fecha),
    INDEX idx_operacion (operacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;orial de operaciones
CREATE TABLE IF NOT EXISTS historial_operaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_libro VARCHAR(20) NOT NULL,
    usuario_id VARCHAR(50) NOT NULL,
    operacion ENUM('PRESTAMO', 'DEVOLUCION', 'RENOVACION') NOT NULL,
    fecha DATETIME NOT NULL,
    sede INT NOT NULL,
    datos_adicionales TEXT,
    INDEX idx_fecha (fecha),
    INDEX idx_operacion (operacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
