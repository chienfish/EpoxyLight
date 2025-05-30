import { useState, useEffect } from "react";
import axios from "axios";
import Bar from "../components/Bar";
import "../styles/HistoryPage.css";

function HistoryPage() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    axios
      .get("/logs?type=history")
      .then((res) => setLogs(res.data.transactions || []))
      .catch((err) => console.error("Error fetching history:", err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <Bar />
      <h1>已結束之交易</h1>
      <div className="grid">
        {logs.map((log, index) => {
          const date = log.created_at ? log.created_at.split("T")[0] : "-";
          const orders = log.order_details || [];

          return (
            <div key={index}>
              <h2>交易 ID: {log.transaction_id}</h2>
              <table>
                <tbody>
                  <tr>
                    <td>狀態</td>
                    <td>
                      <span
                        style={{
                          color:
                            log.status === "success"
                              ? "green"
                              : log.status === "cancelled"
                              ? "red"
                              : "#333",
                          fontWeight: "bold",
                        }}
                      >
                        {log.status}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td>交易時間</td>
                    <td>{date}</td>
                  </tr>
                </tbody>
              </table>

              {orders.length > 0 ? (
                <div
                  style={{
                    marginTop: "12px",
                    padding: "8px 12px",
                    background: "#fff",
                    borderRadius: "8px",
                    boxShadow: "inset 0 0 4px rgba(0,0,0,0.05)",
                  }}
                >
                  <h3
                    style={{
                      fontSize: "13px",
                      fontWeight: "bold",
                      marginBottom: "6px",
                      color: "#444",
                    }}
                  >
                    訂單明細
                  </h3>
                  {orders.map((order, i) => (
                    <table
                      key={i}
                      style={{
                        width: "100%",
                        fontSize: "13px",
                        marginBottom: "8px",
                        borderTop: "1px solid #ccc",
                        paddingTop: "6px",
                      }}
                    >
                      <tbody>
                        <tr>
                          <td>商品</td>
                          <td>{order.product_id}</td>
                        </tr>
                        <tr>
                          <td>數量</td>
                          <td>{order.amount}</td>
                        </tr>
                        <tr>
                          <td>單價</td>
                          <td>${order.price}</td>
                        </tr>
                        <tr>
                          <td>總價</td>
                          <td>${order.amount * order.price}</td>
                        </tr>
                      </tbody>
                    </table>
                  ))}
                </div>
              ) : (
                <p style={{ fontStyle: "italic", fontSize: "13px", color: "#555" }}>
                  無訂單資料
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default HistoryPage;
