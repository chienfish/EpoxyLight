from flask import Flask, request, jsonify
import pymysql
import pymongo
import uuid
from datetime import datetime

app = Flask(__name__)
yourpassword = "Aa5849593mm"  # 請替換為你的 MySQL 密碼
# 初始化 MySQL 連線
# mysql_conn = pymysql.connect(
#     host="localhost",
#     user="root",
#     password="yourpassword",
#     database="epoxy",
#     autocommit=False
# )

# 這裡是用來測試的 MySQL 連線，可能還需要修更簡潔一點
def create_database_if_not_exists():
    connection = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password=yourpassword,
        autocommit=True
    )
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS epoxy;")
    connection.close()

create_database_if_not_exists()  # 確保資料庫存在

# 連線進 epoxy 資料庫
mysql_conn = pymysql.connect(
    host="127.0.0.1",
    user="root",
    password=yourpassword,
    database="epoxy",
    autocommit=False
)

# 建立 orders 表格（如果還沒建立）
def init_mysql_tables():
    with mysql_conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                transaction_id VARCHAR(64),
                user VARCHAR(255),
                amount INT,
                timestamp DATETIME
            );
        """)
    mysql_conn.commit()

init_mysql_tables()

# 初始化 MongoDB 連線
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["epoxy"]
inventory_col = mongo_db["inventory"]
log_col = mongo_db["transactions_log"]

inventory_col.insert_many([
    { "item": "apple", "stock": 10 },
    { "item": "banana", "stock": 5 },
    { "item": "coffee", "stock": 8 },
    { "item": "milk", "stock": 6 }
])

# 暫存交易 session
transactions = {}

# 假資料 logs
fake_logs = [
    {
        "transaction_id": "TXN20240513001",
        "status": "success",
        "created_at": "2024-05-13T14:01:22",
        "order_data": {
            "user": "chienfish",
            "amount": 120
        },
        "inventory_data": {
            "item": "apple",
            "count": -2
        },
        "mysql": "ok",
        "mongodb": "ok"
    },
    {
        "transaction_id": "TXN20240513002",
        "status": "cancelled",
        "created_at": "2024-05-13T14:05:00",
        "order_data": {
            "user": "amy",
            "amount": 80
        },
        "inventory_data": {
            "item": "banana",
            "count": -3
        },
        "mysql": "ok",
        "mongodb": "fail: stock not enough"
    },
    {
        "transaction_id": "TXN20240513003",
        "status": "ready",
        "created_at": "2024-05-13T14:10:00",
        "order_data": {
            "user": "bob",
            "amount": 50
        },
        "inventory_data": {
            "item": "milk",
            "count": -1
        },
        "mysql": "ok",
        "mongodb": "ok"
    },
    {
        "transaction_id": "TXN20240513004",
        "status": "pending",
        "created_at": "2024-05-13T14:20:00",
        "order_data": {
            "user": "aaron",
            "amount": 55
        },
        "inventory_data": {
            "item": "coffee",
            "count": -1
        },
        "mysql": "fail",
        "mongodb": "ok"
    }
]

# 狀態分類
STATUS_MAPPING = {
    "status": ["pending", "ready"],
    "history": ["success", "cancelled", "abort"]
}

def write_log(txn_id, data):
    # log_col.update_one()
    pass

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
    data = request.json
    txn_id = data.get("transaction_id")
    order_data = data.get("order_data")
    inventory_data = data.get("inventory_data")

    mysql_success = False
    mongo_success = False

    try:
        # --- MySQL 寫入：用 transaction 包起來 ---
        mysql_conn.begin()
        with mysql_conn.cursor() as cursor:
            sql = """
                INSERT INTO orders (transaction_id, user, amount, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                txn_id,
                order_data["user"],
                order_data["amount"],
                datetime.now()
            ))
        mysql_success = True

        # --- MongoDB session transaction ---
        mongo_session = mongo_client.start_session()
        mongo_session.start_transaction()

        item = inventory_data["item"]
        count = inventory_data["count"]  # 要扣除的數量：通常是負數

        result = inventory_col.update_one(
            {"item": item, "stock": {"$gte": abs(count)}},  # 確保夠扣
            {"$inc": {"stock": count}},
            session=mongo_session
        )

        if result.modified_count == 0:
            raise Exception("MongoDB: insufficient stock")

        mongo_success = True

        # --- 兩邊都成功，寫入準備完成 log，不 commit ---
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "prepare",
                "mysql": "ok",
                "mongodb": "ok",
                "status": "ready",
                "order_data": order_data,
                "inventory_data": inventory_data
            }}
        )

        # 暫時不 commit，由 /commit 負責
        return jsonify({"transaction_id": txn_id, "status": "ready"})

    except Exception as e:
        print(f"[Prepare Error] {e}")

        # 回滾 MySQL
        if mysql_success:
            mysql_conn.rollback()

        # 回滾 MongoDB
        if mongo_success:
            mongo_session.abort_transaction()

        # 更新 log：標記失敗
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

    finally:
        if 'mongo_session' in locals():
            mongo_session.end_session()


@app.route("/commit", methods=["POST"])
def commit():
    data = request.json
    txn_id = data.get("transaction_id")

    # 查詢 log 取得 mongo session 狀態（假設 session 需要保留）
    log_entry = log_col.find_one({"transaction_id": txn_id})
    if not log_entry or log_entry.get("status") != "ready":
        return jsonify({"error": "Transaction not ready or not found"}), 400

    try:
        # 1. Commit MySQL
        mysql_conn.commit()

        # 2. Commit MongoDB
        mongo_session = mongo_client.start_session()
        mongo_session.start_transaction()
        mongo_session.commit_transaction()

        # 3. 更新 log 狀態
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "commit",
                "status": "success"
            }}
        )

        return jsonify({"transaction_id": txn_id, "status": "success"})

    except Exception as e:
        # 有任何問題就回滾
        mysql_conn.rollback()
        mongo_session.abort_transaction()

        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "commit",
                "status": "commit_failed",
                "error": str(e)
            }}
        )

        return jsonify({"transaction_id": txn_id, "status": "commit_failed", "error": str(e)}), 500

    finally:
        if 'mongo_session' in locals():
            mongo_session.end_session()


@app.route("/rollback", methods=["POST"])
def rollback():
    data = request.json
    txn_id = data.get("transaction_id")

    log_entry = log_col.find_one({"transaction_id": txn_id})
    if not log_entry:
        return jsonify({"error": "Transaction not found"}), 404

    try:
        # 1. 回滾 MySQL 訂單（根據 txn_id 刪除）
        with mysql_conn.cursor() as cursor:
            cursor.execute("DELETE FROM orders WHERE transaction_id = %s", (txn_id,))
        mysql_conn.commit()

        # 2. 回滾 MongoDB 庫存（加回來）← 可根據 log 中紀錄補回
        if "inventory_data" in log_entry:
            item = log_entry["inventory_data"]["item"]
            count = log_entry["inventory_data"]["count"]
            inventory_col.update_one(
                {"item": item},
                {"$inc": {"stock": -count}}  # 將扣掉的加回去
            )

        # 3. 更新 log 狀態
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
        filtered_logs = [log for log in fake_logs if log["status"] in STATUS_MAPPING[log_type]]
    else:
        filtered_logs = fake_logs
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
    found = next((log for log in fake_logs if log["transaction_id"] == txn_id), None)
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