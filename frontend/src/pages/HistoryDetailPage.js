// src/pages/HistoryDetailPage.jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import Bar from "../components/Bar";
import "../styles/HistoryDetailPage.css";

function HistoryDetailPage() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    axios.get(`/status/${id}`).then((res) => setDetail(res.data));
  }, [id]);

  if (!detail) return <div>Loading...</div>;

  return (
    <div className="min-h-screen bg-white">
      <Bar />
      <div className="p-8 text-center">
        <h1 className="text-xl font-bold">ID: {detail.id}</h1>
        <h2 className="text-lg font-semibold mt-2">Status: {detail.status}</h2>
        <p className="text-gray-600 mt-1">建立時間: {detail.start_time}</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-10 text-sm">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">📦 Database</h3>
            <ul className="text-left">
              <li>✔️ MySQL 寫入成功（{detail.mysql_status}）</li>
              <li>✔️ MongoDB 更新成功（{detail.mongo_status}）</li>
            </ul>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">🛒 訂單內容</h3>
            <p>{detail.inventory_data?.item} × {-1 * detail.inventory_data?.count} (${detail.order_data?.amount})</p>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">⏱️ 執行時間</h3>
            <p>3.2 秒（模擬）</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HistoryDetailPage;
