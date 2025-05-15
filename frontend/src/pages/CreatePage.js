import { useEffect, useState } from "react";
import Bar from "../components/Bar";
import "../styles/CreatePage.css";

function CreatePage() {
    const [items, setItems] = useState([]);
    const [item, setItem] = useState("");
    const [count, setCount] = useState(-1);
    const [user, setUser] = useState("");
    const [amount, setAmount] = useState(0);
    const [result, setResult] = useState(null);

    // 取得 MongoDB 商品清單
    useEffect(() => {
        fetch("/items")
            .then(res => res.json())
            .then(data => {
                setItems(data.items || []);
                setItem(data.items?.[0] || "");
            });
    }, []);

    const handleSubmit = async () => {
        try {
            // 1. /begin
            const beginRes = await fetch("/begin", { method: "POST" });
            const beginData = await beginRes.json();
            const txnId = beginData.transaction_id;

            // 2. /prepare
            await fetch("/prepare", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ transaction_id: txnId, item, count, user, amount }),
            });

            // 3. /commit
            const commitRes = await fetch("/commit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ transaction_id: txnId }),
            });

            const commitData = await commitRes.json();

            setResult({
                success: true,
                txnId,
                status: commitData.status || "ready",
            });
        } catch (error) {
            console.error(error);
            setResult({ success: false });
        }
    };

    return (
        <div className="create-container">
            <Bar />
            <div className="form-card">
                <h2>建立交易</h2>
                <div className="form-grid">
                    <div className="form-group">
                        <label>商品類型</label>
                        <select value={item} onChange={e => setItem(e.target.value)}>
                            {items.map((itm, idx) => (
                                <option key={idx} value={itm}>{itm}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label>數量</label>
                        <input type="number" value={count} onChange={e => setCount(Number(e.target.value))} />
                    </div>
                    <div className="form-group">
                        <label>使用者</label>
                        <input type="text" value={user} onChange={e => setUser(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label>金額</label>
                        <input type="number" value={amount} onChange={e => setAmount(Number(e.target.value))} />
                    </div>
                    <button
                        className="submit-btn"
                        onClick={handleSubmit}
                        disabled={
                            !item || !user || count === null || count === "" || amount === 0
                        }
                    >
                        🔍
                    </button>
                </div>
            </div>

            {result && result.success && (
                <div className="result-block">
                    <p>✅ 成功</p>
                    <p>- Transaction ID: {result.txnId}</p>
                    <p>- 狀態：{result.status}</p>
                    <p>- 系統已完成準備，您可以選擇送出 commit 或中止交易 rollback。</p>
                </div>
            )}
            {result && !result.success && (
                <div className="result-block error">❌ 發生錯誤，請稍後再試。</div>
            )}
        </div>
    );
}

export default CreatePage;
