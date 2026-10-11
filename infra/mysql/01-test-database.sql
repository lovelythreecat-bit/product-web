-- Development container only. This user can never access the development database.
CREATE DATABASE IF NOT EXISTS ecommerce_ai_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'ecommerce_test'@'%' IDENTIFIED BY 'TEST_ONLY_test_local';
GRANT ALL PRIVILEGES ON ecommerce_ai_test.* TO 'ecommerce_test'@'%';

-- T07 relational admission starts in this preserved, isolated schema.
-- Keep ecommerce_ai_test and its historical ledger records intact.
CREATE DATABASE IF NOT EXISTS ecommerce_ai_test_t07_20261011 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON ecommerce_ai_test_t07_20261011.* TO 'ecommerce_test'@'%';
