-- Development container only. This user can never access the development database.
CREATE DATABASE IF NOT EXISTS ecommerce_ai_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'ecommerce_test'@'%' IDENTIFIED BY 'TEST_ONLY_test_local';
GRANT ALL PRIVILEGES ON ecommerce_ai_test.* TO 'ecommerce_test'@'%';
