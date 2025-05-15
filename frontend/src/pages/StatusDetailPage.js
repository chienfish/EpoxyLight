import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Bar from "../components/Bar";
import "../styles/StatusDetailPage.css";
import { FaDatabase } from "react-icons/fa6";
import { MdDataset } from "react-icons/md";
import { FaStore } from "react-icons/fa";

function StatusDetailPage() {
    const { id } = useParams();
    const [detail, setDetail] = useState(null);
    const [rolledBack, setRolledBack] = useState(false);
    const [committed, setCommitted] = useState(false);

    useEffect(() => {
        fetch(`/status/${id}`)
            .then(res => res.json())
            .then(data => {
                setDetail(data);

                const mysqlFail = data.mysql_status === "fail";
                const mongoFail = data.mongo_status === "fail";

                // 自動 rollback 條件
                if ((mysqlFail || mongoFail) && !rolledBack) {
                    fetch("/rollback", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ transaction_id: id }),
                    }).then(() => {
                        alert("⚠️ 系統偵測到失敗，自動執行 rollback");
                        setRolledBack(true);
                    });
                }
            });
    }, [id, rolledBack]);

    const handleManualRollback = async () => {
        await fetch("/rollback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: id }),
        });
        alert("🔁 已手動觸發 rollback");
        setRolledBack(true);
    };

    const handleCommit = async () => {
        await fetch("/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: id }),
        });
        alert("✅ 成功送出 commit");
        setCommitted(true);
    };

    if (!detail) return <div className="status-detail"><Bar /><p>Loading...</p></div>;

    const isMySQLOK = detail.mysql_status === "ok";
    const isMongoOK = detail.mongo_status === "ok";
    const isMySQLFail = detail.mysql_status === "fail";
    const isMongoFail = detail.mongo_status === "fail";
    const isReady = detail.status === "ready";

    const allowCommit = isReady || (isMySQLOK && isMongoOK);
    const allowRollback = !isMySQLFail && !isMongoFail && !allowCommit && !rolledBack;

    return (
        <div className="status-detail">
            <Bar />
            <h2>ID: {detail.id}</h2>
            <h3>Status: {detail.status}</h3>
            <p>建立時間: {detail.start_time}</p>

            <div className="detail-grid">
                <div className="detail-card">
                    <div className="icon"><FaDatabase /></div>
                    <b>Database</b>
                    <p>MySQL: {detail.mysql_status}</p>
                    <p>MongoDB: {detail.mongo_status}</p>
                </div>

                <div className="detail-card">
                    <div className="icon"><MdDataset /></div>
                    <b>Order 資料</b>
                    <pre>{JSON.stringify(detail.order_data, null, 2)}</pre>
                </div>

                <div className="detail-card">
                    <div className="icon"><FaStore /></div>
                    <b>Inventory 資料</b>
                    <pre>{JSON.stringify(detail.inventory_data, null, 2)}</pre>
                </div>
            </div>

            {allowCommit && !committed && (
                <button className="commit-btn" onClick={handleCommit}>✅ 手動 commit</button>
            )}

            {allowRollback && (
                <button className="rollback-btn" onClick={handleManualRollback}>🔁 手動 rollback</button>
            )}
        </div>
    );
}

export default StatusDetailPage;
