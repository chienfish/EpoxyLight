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

    # 動態建立 orders_staging 表（如果尚未存在）
    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders_staging (
                    transaction_id VARCHAR(64),
                    product_id VARCHAR(64),
                    amount INT,
                    PRIMARY KEY (transaction_id, product_id)
                )
            """)
        mysql_conn.commit()
    except Exception as e:
        return jsonify({"message": f"Failed to create staging table: {str(e)}"}), 500

    # MongoDB prepare
    for item in products:
        product = inventory_col.find_one({"_id": item['product_id']})
        if not product:
            mongo_ok = False
            break

        if product['stock'] >= item['amount']:
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

    # MySQL prepare
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

        log = log_col.find_one({"transaction_id": txn_id})
        if log.get("mysql") == "ok" and log.get("mongodb") == "ok":
            log_col.update_one(
                {"transaction_id": txn_id},
                {
                    "$set": {
                        "status": "ready",
                        "phase": "prepare",
                        "prepare_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                    }
                }
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
            # 取得 staging 資料
            cursor.execute(
                "SELECT product_id, amount FROM orders_staging WHERE transaction_id = %s",
                (txn_id,)
            )
            staging_orders = cursor.fetchall()

            for product_id, amount in staging_orders:
                # 從 MongoDB 查詢商品價格
                product = inventory_col.find_one({"_id": product_id})
                if not product:
                    raise Exception(f"Product {product_id} not found in MongoDB")
                price = product["price"]
                total_price = amount * price

                # 寫入正式訂單（新增 transaction_id）
                cursor.execute(
                    """
                    INSERT INTO orders (transaction_id, product_id, amount, price, create_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (txn_id, product_id, amount, total_price)
                )

            # 清空暫存訂單
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

    # 查找 log 記錄
    log_entry = log_col.find_one({"transaction_id": txn_id})
    if not log_entry:
        return jsonify({"error": "Transaction not found"}), 404

    if log_entry.get("status") not in ["pending", "ready"]:
        return jsonify({"error": "Only pending or ready transactions can be rolled back"}), 400

    try:
        with mysql_conn.cursor() as cursor:
            # 1. 取得 orders_staging 資料
            cursor.execute("""
                SELECT product_id, amount
                FROM orders_staging
                WHERE transaction_id = %s
            """, (txn_id,))
            staging_orders = cursor.fetchall()

            if not staging_orders:
                return jsonify({"error": "No staging order found for rollback"}), 400

            # 2. 取得商品價格（從 MongoDB products）
            product_ids = [row[0] for row in staging_orders]
            products = inventory_col.find({"_id": {"$in": product_ids}})
            price_map = {p["_id"]: p.get("price", 0) for p in products}

            # 3. 寫入正式 orders 資料
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for product_id, amount in staging_orders:
                price = price_map.get(product_id, 0)
                cursor.execute("""
                    INSERT INTO orders (transaction_id, product_id, amount, price, create_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (txn_id, product_id, amount, price, now))
            mysql_conn.commit()

            # 4. 刪除 orders_staging 資料
            cursor.execute("DELETE FROM orders_staging WHERE transaction_id = %s", (txn_id,))
            mysql_conn.commit()

        # 5. 刪除 MongoDB inventory_staging 資料
        inventory_staging_col.delete_many({"transaction_id": txn_id})

        # 6. 更新 log
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "rollback",
                "status": "cancelled"
            }}
        )

        return jsonify({"transaction_id": txn_id, "status": "cancelled"})

    except Exception as e:
        import traceback
        traceback.print_exc()

        # 回滾失敗寫入錯誤
        log_col.update_one(
            {"transaction_id": txn_id},
            {"$set": {
                "phase": "rollback",
                "status": "rollback_failed",
                "error": str(e)
            }}
        )

        return jsonify({
            "transaction_id": txn_id,
            "status": "rollback_failed",
            "error": str(e)
        }), 500



@app.route("/logs", methods=["GET"])
def get_logs():
    log_type = request.args.get("type")

    STATUS_MAPPING = {
        "status": ["pending", "ready"],
        "pending": ["pending", "ready"],
        "history": ["success", "cancelled"]
    }

    if log_type in STATUS_MAPPING:
        query = { "status": { "$in": STATUS_MAPPING[log_type] } }
    else:
        query = {}

    logs = list(log_col.find(query, {"_id": 0}))

    if log_type == "history":
        try:
            txn_ids = [log["transaction_id"] for log in logs]
            if not txn_ids:
                return jsonify({ "transactions": [] })

            with mysql_conn.cursor() as cursor:
                format_str = ",".join(["%s"] * len(txn_ids))
                query = f"""
                    SELECT transaction_id, product_id, amount, price, create_at
                    FROM orders
                    WHERE transaction_id IN ({format_str})
                """
                cursor.execute(query, tuple(txn_ids))
                rows = cursor.fetchall()

            # 建立 transaction_id -> list of orders
            txn_map = {}
            date_map = {}
            for txn_id, product_id, amount, price, created_at in rows:
                txn_map.setdefault(txn_id, []).append({
                    "product_id": product_id,
                    "amount": amount,
                    "price": price
                })
                # 儲存該 transaction 的時間（只取一筆）
                if txn_id not in date_map:
                    date_map[txn_id] = created_at.strftime("%Y-%m-%d")

            for log in logs:
                txn_id = log["transaction_id"]
                log["order_details"] = txn_map.get(txn_id, [])
                log["created_at"] = date_map.get(txn_id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    return jsonify({ "transactions": logs })

@app.route("/items", methods=["GET"])
def get_items():
    products = inventory_col.find({}, {"_id": 1, "name": 1, "price": 1, "stock": 1})
    items = []
    for p in products:
        items.append({
            "id": str(p["_id"]),
            "name": p["name"],
            "price": p["price"],
            "stock": p.get("stock", 0)  # 安全 fallback
        })
    return jsonify({"items": items})

@app.route("/status/<txn_id>", methods=["GET"])
def get_transaction_detail(txn_id):
    log = log_col.find_one({"transaction_id": txn_id}, {"_id": 0})
    if not log:
        return jsonify({"error": "Not found"}), 404

    # 取得 orders_staging 的訂單內容
    with mysql_conn.cursor() as cursor:
        cursor.execute(
            "SELECT product_id, amount FROM orders_staging WHERE transaction_id = %s",
            (txn_id,)
        )
        orders = cursor.fetchall()  # list of (product_id, amount)

    order_data = []
    inventory_data = []
    product_ids = [row[0] for row in orders]

    # 從 Mongo 取出所有相關商品
    mongo_products = {p["_id"]: p for p in inventory_col.find(
        {"_id": {"$in": product_ids}}, {"_id": 1, "name": 1, "price": 1, "stock": 1}
    )}

    # 整理 order_data
    for product_id, amount in orders:
        product = mongo_products.get(product_id)
        if product:
            unit_price = product["price"]
            order_data.append({
                "product_id": product_id,
                "product_name": product["name"],
                "amount": amount,
                "unit_price": unit_price,
                "total_price": unit_price * amount
            })

    # 整理 inventory_data
    for product_id in product_ids:
        product = mongo_products.get(product_id)
        if product:
            inventory_data.append({
                "product_id": product_id,
                "product_name": product["name"],
                "price": product["price"],
                "stock": product["stock"]
            })

    return jsonify({
        "transaction_id": log["transaction_id"],
        "status": log.get("status", ""),
        "start_time": log.get("start_time", "").isoformat() if isinstance(log.get("start_time"), datetime) else str(log.get("start_time")),
        "mysql": log.get("mysql", ""),
        "mongodb": log.get("mongodb", ""),
        "order_data": order_data,
        "inventory_data": inventory_data
    })

if __name__ == "__main__":
    app.run(debug=True)