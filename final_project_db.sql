CREATE DATABASE IF NOT EXISTS DB_order;
USE DB_order;

-- 正式訂單資料表
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(20) NOT NULL,
    amount INT NOT NULL,
    price INT NOT NULL,
    create_at DATETIME NOT NULL
);

-- 暫存訂單資料表
CREATE TABLE IF NOT EXISTS orders_staging (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(20) NOT NULL,
    amount INT NOT NULL
);

-- 插入 5 筆正式訂單資料
INSERT INTO orders (product_id, amount, price, create_at) VALUES
('p001', 1, 20000, NOW()),   -- iPad Pro
('p002', 2, 80000, NOW()),   -- MacBook Air
('p003', 1, 10000, NOW()),   -- Apple Watch
('p004', 3, 90000, NOW()),   -- iPhone 15
('p005', 1, 5000, NOW());   -- AirPods Pro

-- 模擬一筆交易中的 staging 訂單
INSERT INTO orders_staging (transaction_id, product_id, amount) VALUES
('tx999', 'p001', 1),
('tx999', 'p002', 1);
