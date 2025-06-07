CREATE DATABASE IF NOT EXISTS DB_order;
USE DB_order;

-- 正式訂單資料表
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(20) NOT NULL,
    amount INT NOT NULL,
    price INT NOT NULL,
    create_at DATETIME NOT NULL
);

-- 暫存訂單資料表
-- DROP TABLE IF EXISTS orders_staging;
-- CREATE TABLE orders_staging (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     transaction_id VARCHAR(50) NOT NULL,
--     product_id VARCHAR(20) NOT NULL,
--     amount INT NOT NULL
-- );

-- 範例正式訂單資料（含 transaction_id）
-- INSERT INTO orders (transaction_id, product_id, amount, price, create_at) VALUES
-- ('txn001', 'p001', 1, 20000, NOW()),   -- iPad Pro
-- ('txn002', 'p002', 2, 80000, NOW()),   -- MacBook Air
-- ('txn003', 'p003', 1, 10000, NOW()),   -- Apple Watch
-- ('txn004', 'p004', 3, 90000, NOW()),   -- iPhone 15
-- ('txn005', 'p005', 1, 5000,  NOW());   -- AirPods Pro

-- 範例暫存訂單資料（尚未 commit）
-- INSERT INTO orders_stagings
