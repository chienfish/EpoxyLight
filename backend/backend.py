from flask import Flask, request, jsonify
import pymysql
import pymongo
from pymongo import UpdateOne
import uuid
from datetime import datetime

# mysql 資料匯入: mysql -u root -p < final_project_db.sql
# mongo 資料匯入: mongo < mongodb_init.txt

# mongo 連線 / 初始化
app = Flask(__name__)
yourpassword = "yourpassword"  # 請替換為你的 MySQL 密碼
sql_dbname = "DB_order"
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["shopdb"]
inventory_col = mongo_db["products"]
log_col = mongo_db["transaction_log"]
inventory_staging_col = mongo_db["products_staging"]

# mysql 連線
mysql_conn = pymysql.connect(
    host="127.0.0.1",
    user="root",
    port=3307,
    password=yourpassword,
    database="DB_order",
    autocommit=False
)

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
    
@app.route('/prepare', methods=['POST'])
def prepare():
    data = request.get_json()
    txn_id = data['transaction_id']
    products = data['products']
    mongo_ok = True

    for item in products:
        product = inventory_col.find_one({"_id": item['product_id']})
        if not product:
            mongo_ok = False
            break

        if product['stock'] >= item['amount']:
            # 僅寫入 staging，不扣庫存
            inventory_staging_col.insert_one({
                "transaction_id": txn_id,
                "product_id": item['product_id'],
                "delta_stock": -item['amount']
            })
        else:
            mongo_ok = False
            break

    if mongo_ok:
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {"mongodb": "ok"}}
        )
    else:
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {"mongodb": "fail"}}
        )
        return jsonify({"message": "MongoDB prepare failed"}), 400

    try:
        with mysql_conn.cursor() as cursor:
            for item in products:
                cursor.execute(
                    "INSERT INTO orders_staging (transaction_id, product_id, amount) VALUES (%s, %s, %s)",
                    (txn_id, item['product_id'], item['amount'])
                )
        mysql_conn.commit()

        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {"mysql": "ok"}}
        )

        # 若兩邊皆 ok，更新 status 為 ready
        log = log_col.find_one({"transaction_id": txn_id})
        if log.get("mysql") == "ok" and log.get("mongodb") == "ok":
            log_col.update_one(
                {"transaction_id": txn_id},
                {"$set": {"status": "ready"}}
            )

        return jsonify({"message": "Prepare OK"}), 200
    except Exception as e:
        mysql_conn.rollback()
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {"mysql": "fail"}}
        )
        return jsonify({"message": f"MySQL prepare failed: {str(e)}"}), 500

@app.route("/commit", methods=["POST"])
def commit():
    data = request.get_json()
    txn_id = data.get("transaction_id")

    log_entry = log_col.find_one({"transaction_id": txn_id})
    if not log_entry:
        return jsonify({"error": "Transaction not found"}), 404

    if log_entry.get("phase") == "rollback":
        return jsonify({"error": "Transaction already rolled back"}), 400

    if log_entry.get("status") != "ready":
        return jsonify({"error": "Transaction not ready for commit"}), 400

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute(
                "SELECT product_id, amount FROM orders_staging WHERE transaction_id = %s",
                (txn_id,)
            )
            staging_orders = cursor.fetchall()

            for product_id, amount in staging_orders:
                product = inventory_col.find_one({"_id": product_id})
                if not product:
                    raise Exception(f"Product {product_id} not found in MongoDB")
                price = product["price"]
                total_price = amount * price

                cursor.execute(
                    "INSERT INTO orders (product_id, amount, price, create_at) VALUES (%s, %s, %s, NOW())",
                    (product_id, amount, total_price)
                )

            cursor.execute(
                "DELETE FROM orders_staging WHERE transaction_id = %s",
                (txn_id,)
            )

        mysql_conn.commit()

        # 真正扣除庫存
        staging_products = inventory_staging_col.find({"transaction_id": txn_id})
        for p in staging_products:
            inventory_col.update_one(
                {"_id": p["product_id"]},
                {"$inc": {"stock": p["delta_stock"]}}  # delta_stock 是負數
            )
        inventory_staging_col.delete_many({"transaction_id": txn_id})

        # 更新 log
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
                "phase": "rollback",
                "status": "cancelled",
                "rollback_reason": str(e)
            }}
        )
        return jsonify({
            "transaction_id": txn_id,
            "status": "cancelled",
            "error": str(e)
        }), 500

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