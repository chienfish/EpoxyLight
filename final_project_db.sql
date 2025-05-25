/* create and use database */
CREATE DATABASE DB_order;
USE DB_order;

-- 正式訂單表
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id VARCHAR(20) NOT NULL,
    amount INT NOT NULL,
    create_at DATETIME NOT NULL
);

-- 暫存訂單表（模擬交易中）
CREATE TABLE orders_staging (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id VARCHAR(20) NOT NULL,
    amount INT NOT NULL,
    transaction_id VARCHAR(50) NOT NULL
);

-- 插入 5 筆正式訂單資料
INSERT INTO orders (user_id, product_id, amount, create_at) VALUES
(1001, 'p001', 1, NOW()),   -- iPad Pro
(1002, 'p002', 2, NOW()),   -- MacBook Air
(1003, 'p003', 1, NOW()),   -- Apple Watch
(1004, 'p004', 3, NOW()),   -- iPhone 15
(1005, 'p005', 1, NOW());   -- AirPods Pro

-- 插入 1 筆 staging 訂單（模擬交易中）
INSERT INTO orders_staging (user_id, product_id, amount, transaction_id) VALUES
(1006, 'p001', 1, 'tx999');  -- 準備再買一台 iPad Pro

/* drop database */
-- DROP DATABASE DB_order;
