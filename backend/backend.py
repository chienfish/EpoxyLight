import os
import json
from flask import Flask, request, jsonify
import pymysql
import pymongo
import uuid
from datetime import datetime

# ---- Local log util ----
LOG_FILE = "logs/transaction_log.jsonl"
os.makedirs("logs", exist_ok=True)

def write_log(entry):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def update_log(txn_id, updates):
    logs = []
    updated = False
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry["transaction_id"] == txn_id:
                    entry.update(updates)
                    updated = True
                logs.append(entry)
    if updated:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            for entry in logs:
                f.write(json.dumps(entry) + "\n")

def get_log(txn_id=None, query_status=None):
    result = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if txn_id and entry.get("transaction_id") != txn_id:
                    continue
                if query_status and entry.get("status") not in query_status:
                    continue
                result.append(entry)
    return result

# ---- Flask init ----
app = Flask(__name__)
yourpassword = "yourpassword"
sql_dbname = "DB_order"
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["shopdb"]
inventory_col = mongo_db["products"]
inventory_staging_col = mongo_db["products_staging"]

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
    write_log(log)

    return jsonify({"transaction_id": txn_id, "status": "pending"})

@app.route("/prepare", methods=["POST"])
def prepare():
    data = request.get_json()
    txn_id = data['transaction_id']
    products = data['products']
    mongo_ok = True

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

    for item in products:
        product = inventory_col.find_one({"_id": item['product_id']})
        if not product or product['stock'] < item['amount']:
            mongo_ok = False
            break

        inventory_staging_col.insert_one({
            "transaction_id": txn_id,
            "product_id": item['product_id'],
            "delta_stock": -item['amount']
        })

    if mongo_ok:
        update_log(txn_id, {"mongodb": "ok"})
    else:
        update_log(txn_id, {"mongodb": "fail"})
        return jsonify({"message": "MongoDB prepare failed"}), 400

    try:
        with mysql_conn.cursor() as cursor:
            for item in products:
                cursor.execute(
                    "INSERT INTO orders_staging (transaction_id, product_id, amount) VALUES (%s, %s, %s)",
                    (txn_id, item['product_id'], item['amount'])
                )
        mysql_conn.commit()
        update_log(txn_id, {"mysql": "ok"})

        log = get_log(txn_id=txn_id)[0]
        if log.get("mysql") == "ok" and log.get("mongodb") == "ok":
            update_log(txn_id, {
                "status": "ready",
                "phase": "prepare",
                "prepare_time": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            })

        return jsonify({"message": "Prepare OK"}), 200

    except Exception as e:
        mysql_conn.rollback()
        update_log(txn_id, {"mysql": "fail"})
        return jsonify({"message": f"MySQL prepare failed: {str(e)}"}), 500

@app.route("/commit", methods=["POST"])
def commit():
    data = request.get_json()
    txn_id = data.get("transaction_id")

    log_entry = get_log(txn_id=txn_id)
    if not log_entry:
        return jsonify({"error": "Transaction not found"}), 404

    log_entry = log_entry[0]

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
                    """
                    INSERT INTO orders (transaction_id, product_id, amount, price, create_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (txn_id, product_id, amount, total_price)
                )

            cursor.execute(
                "DELETE FROM orders_staging WHERE transaction_id = %s",
                (txn_id,)
            )

        mysql_conn.commit()

        staging_products = inventory_staging_col.find({"transaction_id": txn_id})
        for p in staging_products:
            inventory_col.update_one(
                {"_id": p["product_id"]},
                {"$inc": {"stock": p["delta_stock"]}}
            )
        inventory_staging_col.delete_many({"transaction_id": txn_id})

        update_log(txn_id, {
            "phase": "commit",
            "status": "success"
        })

        return jsonify({"transaction_id": txn_id, "status": "success"})

    except Exception as e:
        mysql_conn.rollback()
        update_log(txn_id, {
            "phase": "rollback",
            "status": "cancelled",
            "rollback_reason": str(e)
        })
        return jsonify({
            "transaction_id": txn_id,
            "status": "cancelled",
            "error": str(e)
        }), 500

@app.route("/rollback", methods=["POST"])
def rollback():
    data = request.json
    txn_id = data.get("transaction_id")

    log_entry = get_log(txn_id=txn_id)
    if not log_entry:
        return jsonify({"error": "Transaction not found"}), 404

    log_entry = log_entry[0]

    if log_entry.get("status") not in ["pending", "ready"]:
        return jsonify({"error": "Only pending or ready transactions can be rolled back"}), 400

    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("""
                SELECT product_id, amount
                FROM orders_staging
                WHERE transaction_id = %s
            """, (txn_id,))
            staging_orders = cursor.fetchall()

            if not staging_orders:
                return jsonify({"error": "No staging order found for rollback"}), 400

            product_ids = [row[0] for row in staging_orders]
            products = inventory_col.find({"_id": {"$in": product_ids}})
            price_map = {p["_id"]: p.get("price", 0) for p in products}

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for product_id, amount in staging_orders:
                price = price_map.get(product_id, 0)
                cursor.execute("""
                    INSERT INTO orders (transaction_id, product_id, amount, price, create_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (txn_id, product_id, amount, price, now))
            mysql_conn.commit()

            cursor.execute("DELETE FROM orders_staging WHERE transaction_id = %s", (txn_id,))
            mysql_conn.commit()

        inventory_staging_col.delete_many({"transaction_id": txn_id})

        update_log(txn_id, {
            "phase": "rollback",
            "status": "cancelled"
        })

        return jsonify({"transaction_id": txn_id, "status": "cancelled"})

    except Exception as e:
        update_log(txn_id, {
            "phase": "rollback",
            "status": "rollback_failed",
            "error": str(e)
        })

        return jsonify({
            "transaction_id": txn_id,
            "status": "rollback_failed",
            "error": str(e)
        }), 500

@app.route("/status/<txn_id>", methods=["GET"])
def get_transaction_detail(txn_id):
    log_entry = get_log(txn_id=txn_id)
    if not log_entry:
        return jsonify({"error": "Not found"}), 404
    log = log_entry[0]

    with mysql_conn.cursor() as cursor:
        cursor.execute(
            "SELECT product_id, amount FROM orders_staging WHERE transaction_id = %s",
            (txn_id,)
        )
        orders = cursor.fetchall()

    order_data = []
    inventory_data = []
    product_ids = [row[0] for row in orders]

    mongo_products = {p["_id"]: p for p in inventory_col.find(
        {"_id": {"$in": product_ids}}, {"_id": 1, "name": 1, "price": 1, "stock": 1}
    )}

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
        "start_time": log.get("start_time", ""),
        "mysql": log.get("mysql", ""),
        "mongodb": log.get("mongodb", ""),
        "order_data": order_data,
        "inventory_data": inventory_data
    })

@app.route("/items", methods=["GET"])
def get_items():
    products = inventory_col.find({}, {"_id": 1, "name": 1, "price": 1, "stock": 1})
    items = []
    for p in products:
        items.append({
            "id": str(p["_id"]),
            "name": p["name"],
            "price": p["price"],
            "stock": p.get("stock", 0)
        })
    return jsonify({"items": items})

@app.route("/logs", methods=["GET"])
def get_logs():
    log_type = request.args.get("type")

    STATUS_MAPPING = {
        "status": ["pending", "ready"],
        "pending": ["pending", "ready"],
        "history": ["success", "cancelled"]
    }

    if log_type in STATUS_MAPPING:
        logs = get_log(query_status=STATUS_MAPPING[log_type])
    else:
        logs = get_log()

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

if __name__ == "__main__":
    app.run(debug=True)
