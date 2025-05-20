import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Bar from "../components/Bar";
import "../styles/StatusPage.css";

function StatusPage() {
    const [transactions, setTransactions] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        fetch("/logs?type=status")
            .then(res => res.json())
            .then(data => setTransactions(data || []));
    }, []);

    const handleCommit = async (txnId) => {
        await fetch("/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: txnId }),
        });
        window.location.reload();
    };

    const handleRollback = async (txnId) => {
        await fetch("/rollback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: txnId }),
        });
        window.location.reload();
    };

    const handleDetail = (txnId) => {
        navigate(`/status/${txnId}`);
    };

    return (
        <div className="status-container">
            <Bar />
            <h2>進行中交易</h2>
            <div className="transaction-grid">
                {transactions.map(txn => (
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
                                    <td>{txn.created_at?.replace("T", " ")}</td>
                                </tr>
                                <tr>
                                    <td>詳情</td>
                                    <td><button onClick={() => handleDetail(txn.transaction_id)}>🔍</button></td>
                                </tr>
                                <tr>
                                    <td>送出 commit</td>
                                    <td><button onClick={() => handleCommit(txn.transaction_id)}>✅</button></td>
                                </tr>
                                <tr>
                                    <td>手動 rollback</td>
                                    <td><button onClick={() => handleRollback(txn.transaction_id)}>🔁</button></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default StatusPage;
