from flask import Flask, request, jsonify
import pymysql
import pymongo
from pymongo import UpdateOne
import uuid
from datetime import datetime

app = Flask(__name__)
yourpassword = "yourpassword"  # 請替換為你的 MySQL 密碼
sql_dbname = "DB_order"

def init_mysql_schema():
    # 連線時不指定資料庫，方便建立 DB
    connection = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password=yourpassword,
        autocommit=True
    )
    with connection.cursor() as cursor:
        # 建立資料庫 + 切換
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {sql_dbname};")
        cursor.execute(f"USE {sql_dbname};")

        # 建立正式 orders 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id VARCHAR(20) NOT NULL,
                amount INT NOT NULL,
                create_at DATETIME NOT NULL
            );
        """)

        # 建立暫存 products_staging 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products_staging (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id VARCHAR(20) NOT NULL,
                amount INT NOT NULL,
                transaction_id VARCHAR(50) NOT NULL
            );
        """)
    connection.close()

init_mysql_schema()

# 重新連線進 DB_order，做後續操作
mysql_conn = pymysql.connect(
    host="127.0.0.1",
    user="root",
    password=yourpassword,
    database="DB_order",
    autocommit=False
)


# 初始化 MongoDB 連線
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["shopdb"]
inventory_col = mongo_db["products"]
log_col = mongo_db["transactions_log"]
inventory_staging_col = mongo_db["products_staging"]

# 還需要MongoDB資料
inventory_col.delete_many({})
inventory_staging_col.delete_many({})
mongo_data=[
  { "_id": "p001", "name": "iPad Pro", "stock": 50}, 
  { "_id": "p002", "name": "MacBook Air", "stock": 50 }, 
  { "_id": "p003", "name": "Apple Watch", "stock": 50 }, 
  { "_id": "p004", "name": "iPhone 15", "stock": 50 },   
  { "_id": "p005", "name": "AirPods Pro", "stock": 50 } ,
]

operations = [
    UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
    for doc in mongo_data
]

inventory_col.bulk_write(operations)

# 暫存交易 session
transactions = {}

# 狀態分類
STATUS_MAPPING = {
    "status": ["pending", "ready"],
    "history": ["success", "cancelled", "abort"]
}

@app.route("/begin", methods=["POST"])
def begin():
    txn_id = f"TXN{uuid.uuid4().hex}" 
    # txn_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}" 
    now = datetime.now().strftime('%Y/%m/%d %H:%M:%S')

    log = {
        "transaction_id": txn_id,
        "phase": "begin",
        "status": "pending",
        "start_time": now,
        "mysql": "",
        "mongodb": ""
    }
    log_col.insert_one(log)

    return jsonify({"transaction_id": txn_id, "status": "pending"})
    
@app.route("/prepare", methods=["POST"])
def prepare():
    data = request.json #網頁過來的資料
    txn_id = data.get("transaction_id")
    order_data = data.get("order_data")

    mysql_success = False
    mongo_success = False

    try:
        # --- MySQL 寫入 ---
        # 寫在 products_staging 表
        mysql_conn.begin()
        for order in order_data:
            with mysql_conn.cursor() as cursor:
                sql = """
                    INSERT INTO products_staging (user_id, product_id, amount, transaction_id)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    order["user_id"],
                    order["product_id"],
                    order["amount"],
                    txn_id
                ))
        mysql_success = True

        # MongoDB 寫入
        for inv in order_data:
            product = inventory_col.find_one({"_id": inv["product_id"]})
            if not product or product["stock"] < inv["amount"]:
                raise Exception(f"Insufficient stock for product {inv['product_id']}")

            inventory_staging_col.insert_one({
                "_id": f"{inv['product_id']}_{txn_id}",  # composite key
                "product_id": inv["product_id"],
                "name": product["name"],
                "stock": product["stock"] - inv["amount"],
                "transaction_id": txn_id
            })
        mongo_success = True

        # --- 寫 log ---
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "prepare",
                "mysql": "ok",
                "mongodb": "ok",
                "status": "ready",
                "order_data": order_data
            }}
        )

        return jsonify({"transaction_id": txn_id, "status": "ready"})

    except Exception as e:
        if mysql_success:
            mysql_conn.rollback()

        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "prepare",
                "mysql": "ok" if mysql_success else "fail",
                "mongodb": "ok" if mongo_success else "fail",
                "status": "prepare_failed",
                "error": str(e)
            }}
        )
        return jsonify({"transaction_id": txn_id, "status": "prepare_failed", "error": str(e)}), 500



@app.route("/commit", methods=["POST"])
def commit():
    data = request.json
    txn_id = data.get("transaction_id")
    print("debug1")
    log_entry = log_col.find_one({"transaction_id": txn_id})
    if log_entry["phase"] == "rollback":
        return jsonify({"error": "Transaction already rolled back"}), 400
    print("debug2")
    try:
        with mysql_conn.cursor() as cursor:
            print("debug3")
            # 1. 從 staging 取出該交易
            cursor.execute("SELECT * FROM products_staging WHERE transaction_id = %s", (txn_id,))
            rows = cursor.fetchall()

            # 2. 插入到正式 orders 表
            for row in rows:
                cursor.execute("""
                    INSERT INTO orders (user_id, product_id, amount, create_at)
                    VALUES (%s, %s, %s, NOW())
                """, (row[1], row[2], row[3]))  # user_id, product_id, amount
            print("debug4")
            # 3. 刪除 staging 訂單
            cursor.execute("DELETE FROM products_staging WHERE transaction_id = %s", (txn_id,))

        # 提交 MySQL 資料庫操作
        mysql_conn.commit()
        print("debug5")
        # mongoDB 更新庫存
        # 查出該交易的 staging 商品
        staging_product = inventory_staging_col.find({"transaction_id": txn_id})
        print(staging_product)
        for p in staging_product:
            inventory_col.update_one(
                {"_id": p["product_id"]},
                {"$set": {"stock": p["stock"]}}
            )
        # 刪除 staging 商品紀錄
        inventory_staging_col.delete_many({"transaction_id": txn_id})
        print("debug6")
        # 寫 log 狀態為成功
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "commit",
                "status": "success"
            }}
        )

        return jsonify({"transaction_id": txn_id, "status": "success"})

    except Exception as e:
        mysql_conn.rollback()

        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "commit",
                "status": "commit_failed",
                "error": str(e)
            }}
        )
        return jsonify({"transaction_id": txn_id, "status": "commit_failed", "error": str(e)}), 500

@app.route("/rollback", methods=["POST"])
def rollback():
    data = request.json
    txn_id = data.get("transaction_id")

    log_entry = log_col.find_one({"transaction_id": txn_id})
    if not log_entry:
        return jsonify({"error": "Transaction not found"}), 404

    try:
        # 刪除 MySQL 訂單
        with mysql_conn.cursor() as cursor:
            cursor.execute("DELETE FROM orders_staging WHERE transaction_id = %s", (txn_id,))
        mysql_conn.commit()
        # 刪除 MongoDB staging 資料
        inventory_staging_col.delete_many({"transaction_id": txn_id})

        # 更新 log
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "rollback",
                "status": "cancelled"
            }}
        )

        return jsonify({"transaction_id": txn_id, "status": "cancelled"})

    except Exception as e:
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "rollback",
                "status": "rollback_failed",
                "error": str(e)
            }}
        )
        return jsonify({"transaction_id": txn_id, "status": "rollback_failed", "error": str(e)}), 500


@app.route("/logs", methods=["GET"])
def get_logs():
    log_type = request.args.get("type")
    if log_type in STATUS_MAPPING:
        filtered_logs = [log for log in log_col if log["status"] in STATUS_MAPPING[log_type]]
    else:
        filtered_logs = log_col
    return jsonify(filtered_logs)

@app.route("/items", methods=["GET"]) # 要取create page的商品
def get_items():
    # items = inventory_col.distinct("item")
    # return jsonify({"items": items})
    return jsonify({
        "items": ["apple", "banana", "coffee", "milk"]
    })

@app.route("/transactions", methods=["GET"])
def get_transactions():
    return jsonify({
        "transactions": [
            {
                "id": "TXN001",
                "status": "ready",
                "start_time": "2025/05/15 15:30"
            }
        ]
    })

@app.route("/status/<txn_id>", methods=["GET"])
def get_transaction_detail(txn_id):
    found = next((log for log in log_col if log["transaction_id"] == txn_id), None)
    if not found:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "id": found["transaction_id"],
        "status": found["status"],
        "start_time": found["created_at"].replace("T", " "),
        "mysql_status": found.get("mysql", "ok"),
        "mongo_status": found.get("mongodb", "ok"),
        "order_data": found["order_data"],
        "inventory_data": found["inventory_data"]
    })

if __name__ == "__main__":
    app.run(debug=True)