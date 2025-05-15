from flask import Flask, request, jsonify
import pymysql
import pymongo
import uuid
from datetime import datetime

app = Flask(__name__)

# 初始化 MySQL 連線
# mysql_conn = pymysql.connect(
#     host="localhost",
#     user="root",
#     password="yourpassword",
#     database="epoxy",
#     autocommit=False
# )

# 初始化 MongoDB 連線
# mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
# mongo_db = mongo_client["epoxy"]
# inventory_col = mongo_db["inventory"]
# log_col = mongo_db["transactions_log"]

# 暫存交易 session
transactions = {}

def write_log(txn_id, data):
    # log_col.update_one()
    pass

@app.route("/begin", methods=["POST"])
def begin():
    return jsonify({})

@app.route("/prepare", methods=["POST"])
def prepare():
    return jsonify({})

@app.route("/commit", methods=["POST"])
def commit():
    return jsonify({})

@app.route("/rollback", methods=["POST"])
def rollback():
    return jsonify({})

@app.route("/logs", methods=["GET"])
def get_logs():
    return jsonify()

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
    return jsonify({
        "id": txn_id,
        "status": "ready",
        "start_time": "2025/05/15 15:30",
        "mysql_status": "ok",
        "mongo_status": "ok",
        "order_data": {
            "user": "testuser",
            "amount": 120
        },
        "inventory_data": {
            "item": "apple",
            "count": -1
        }
    })

if __name__ == "__main__":
    app.run(debug=True)