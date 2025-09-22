-- Create database
CREATE DATABASE IF NOT EXISTS waste_management;
USE waste_management;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    credit_score INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Landfills table
CREATE TABLE IF NOT EXISTS landfills (
    landfill_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Waste records table
CREATE TABLE IF NOT EXISTS waste_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    landfill_id INT,
    waste_type ENUM('wet', 'dry', 'electronic', 'hazardous', 'other') NOT NULL,
    weight_kg DECIMAL(6,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (landfill_id) REFERENCES landfills(landfill_id) ON DELETE SET NULL
);

-- Insert some sample landfills
INSERT INTO landfills (name, location) VALUES
('Central City Landfill', 'Sector 10, New Town'),
('Northside Recycling Center', 'Near NH-24 Highway'),
('Southside E-Waste Facility', 'Industrial Area Phase 2');
