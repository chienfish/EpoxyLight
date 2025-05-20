import { useState, useEffect } from "react";
import axios from "axios";
import Bar from "../components/Bar";
import { useNavigate } from "react-router-dom";
import "../styles/HistoryPage.css";

function HistoryPage() {
  const [logs, setLogs] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get("/logs?type=history").then((res) => setLogs(res.data));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <Bar />
      <h1 className="text-2xl font-bold text-center py-6">已結束之交易</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 px-10 pb-10">
        {logs.map((log, index) => (
          <div
            key={index}
            className="bg-white rounded-xl shadow-md p-4 text-sm"
          >
            <h2 className="font-semibold text-center mb-2">
              ID: {log.transaction_id}
            </h2>
            <table className="w-full">
              <tbody>
                <tr><td className="font-semibold">狀態</td><td>{log.status}</td></tr>
                <tr><td className="font-semibold">使用者</td><td>{log.order_data?.user || "-"}</td></tr>
                <tr><td className="font-semibold">商品</td><td>{log.inventory_data?.item || "-"}</td></tr>
                <tr><td className="font-semibold">數量</td><td>{-1 * (log.inventory_data?.count || 0)}</td></tr>
                <tr><td className="font-semibold">金額</td><td>{log.order_data?.amount || 0}</td></tr>
                <tr><td className="font-semibold">時間</td><td>{log.created_at?.split("T")[0]}</td></tr>
              </tbody>
            </table>
            <div className="text-right mt-2">
              <button
                onClick={() => navigate(`/history/${log.transaction_id}`)}
                className="text-blue-600 hover:underline"
              >
                🔍 詳細
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default HistoryPage;
