import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Bar from "../components/Bar";
import "../styles/StatusPage.css";

function StatusPage() {
    const [transactions, setTransactions] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        fetch("/logs?type=pending") // 只抓 status = pending 或 ready 的交易
            .then(res => res.json())
            .then(data => setTransactions(data.transactions || []));
    }, []);

    const handleCommit = async (txnId) => {
        await fetch("/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: txnId }),
        });
        navigate("/history");
        };

        const handleRollback = async (txnId) => {
        await fetch("/rollback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: txnId }),
        });
        navigate("/history");
        };

    const handleDetail = (txnId) => {
        navigate(`/status/${txnId}`);
    };

    return (
        <div className="status-container">
            <Bar />
            <h2>進行中交易</h2>
            <div className="transaction-grid">
                {transactions.length === 0 ? (
                    <p style={{ fontSize: "14px", color: "#555", textAlign: "center", marginTop: "20px" }}>
                        🔎 目前沒有進行中交易（pending 或 ready）
                    </p>
                ) : (
                    transactions.map(txn => (
                        <div className="transaction-card" key={txn.transaction_id}>
                            <h3>ID: {txn.transaction_id}</h3>
                            <table>
                                <tbody>
                                    <tr>
                                        <td>狀態</td>
                                        <td>{txn.status}</td>
                                    </tr>
                                    <tr>
                                        <td>開始時間</td>
                                        <td>{new Date(txn.start_time).toLocaleString()}</td>
                                    </tr>
                                    <tr>
                                        <td>詳情</td>
                                        <td><button onClick={() => handleDetail(txn.transaction_id)}>🔍</button></td>
                                    </tr>
                                    <tr>
                                        <td>送出 commit</td>
                                        <td>
                                            <button
                                            onClick={() => {
                                                if (txn.status === "ready") {
                                                if (window.confirm(`確定要對交易 ${txn.transaction_id} 執行 commit 嗎？`)) {
                                                    handleCommit(txn.transaction_id);
                                                }
                                                }
                                            }}
                                            disabled={txn.status !== "ready"}
                                            title={txn.status !== "ready" ? "僅 ready 狀態可執行 commit" : ""}
                                            >
                                            ✅
                                            </button>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>手動 rollback</td>
                                        <td>
                                            <button
                                            onClick={() => {
                                                if (txn.status === "pending" || txn.status === "ready") {
                                                if (window.confirm(`確定要對交易 ${txn.transaction_id} 執行 rollback 嗎？`)) {
                                                    handleRollback(txn.transaction_id);
                                                }
                                                }
                                            }}
                                            disabled={txn.status !== "pending" && txn.status !== "ready"}
                                            title={
                                                txn.status === "success"
                                                ? "已成功提交，無法 rollback"
                                                : txn.status !== "pending" && txn.status !== "ready"
                                                ? "僅 pending 或 ready 狀態可執行 rollback"
                                                : ""
                                            }
                                            >
                                            🔁
                                            </button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

export default StatusPage;
