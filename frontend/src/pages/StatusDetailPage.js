import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Bar from "../components/Bar";
import "../styles/StatusDetailPage.css";
import { FaDatabase } from "react-icons/fa6";
import { MdDataset } from "react-icons/md";
import { FaStore } from "react-icons/fa";

function StatusDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [detail, setDetail] = useState(null);
    const [rolledBack, setRolledBack] = useState(false);
    const [committed, setCommitted] = useState(false);

    useEffect(() => {
        const fetchDetail = async () => {
            const res = await fetch(`/status/${id}`);
            const data = await res.json();
            setDetail(data);
        };

        fetchDetail();
    }, [id]);

    const handleManualRollback = async () => {
        const confirmed = window.confirm("確定要執行 rollback 嗎？\n這將會取消交易並還原所有資料。");
        if (!confirmed) return;

        await fetch("/rollback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: id }),
        });

        alert("🔁 已手動觸發 rollback");
        setRolledBack(true);
        navigate("/history");
    };

    const handleCommit = async () => {
        const confirmed = window.confirm("確定要送出 commit 嗎？\n這將會正式寫入訂單並扣除庫存。");
        if (!confirmed) return;

        await fetch("/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: id }),
        });

        alert("✅ 成功送出 commit");
        setCommitted(true);
        navigate("/history");
    };

    if (!detail) return <div className="status-detail"><Bar /><p>Loading...</p></div>;

    const allowCommit = detail.status === "ready";
    const allowRollback = (detail.status === "pending" || detail.status === "ready") && !rolledBack;

    return (
        <div className="status-detail">
            <Bar />
            <h2>ID: {detail.transaction_id}</h2>
            <h3>Status: {detail.status}</h3>
            <p>建立時間: {new Date(detail.start_time).toLocaleString()}</p>

            <div className="detail-grid">
                <div className="detail-card">
                    <div className="icon"><FaDatabase /></div>
                    <b>Database 狀態</b>
                    <p>MySQL: {detail.mysql}</p>
                    <p>MongoDB: {detail.mongodb}</p>
                </div>

                <div className="detail-card">
                    <div className="icon"><MdDataset /></div>
                    <b>Order 資料</b>
                    {detail.order_data.length > 0 ? (
                        <table className="detail-table">
                            <thead>
                                <tr>
                                    <th>商品</th>
                                    <th>數量</th>
                                    <th>單價</th>
                                    <th>總價</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detail.order_data.map((item, idx) => (
                                    <tr key={idx}>
                                        <td>{item.product_name}</td>
                                        <td>{item.amount}</td>
                                        <td>${item.unit_price}</td>
                                        <td>${item.total_price}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <p>無訂單資料</p>
                    )}
                </div>

                <div className="detail-card">
                    <div className="icon"><FaStore /></div>
                    <b>Inventory 資料</b>
                    {detail.inventory_data.length > 0 ? (
                        <table className="detail-table">
                            <thead>
                                <tr>
                                    <th>商品</th>
                                    <th>價格</th>
                                    <th>庫存</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detail.inventory_data.map((item, idx) => (
                                    <tr key={idx}>
                                        <td>{item.product_name}</td>
                                        <td>${item.price}</td>
                                        <td>{item.stock}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <p>無庫存資料</p>
                    )}
                </div>
            </div>

            <div className="action-buttons">
                {allowCommit && !committed && (
                    <button className="commit-btn" onClick={handleCommit}>✅ 送出 commit</button>
                )}
                {allowRollback && (
                    <button className="rollback-btn" onClick={handleManualRollback}>🔁 手動 rollback</button>
                )}
            </div>
        </div>
    );
}

export default StatusDetailPage;
