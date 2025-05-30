import { useEffect, useState } from "react";
import Bar from "../components/Bar";
import "../styles/CreatePage.css";

function CreatePage() {
    const [items, setItems] = useState([]); // [{ id, name, price }]
    const [itemId, setItemId] = useState("");
    const [count, setCount] = useState(1);
    const [amount, setAmount] = useState(0);
    const [result, setResult] = useState(null);

    useEffect(() => {
        fetch("/items")
            .then(res => res.json())
            .then(data => {
                const list = data.items || [];
                setItems(list);
            });
    }, []);

    useEffect(() => {
        if (itemId) {
            const selected = items.find(i => i.id === itemId);
            if (selected) {
                setCount(1); // 每次換商品重設為 1
                setAmount(selected.price);
            }
        }
    }, [itemId, items]);

    useEffect(() => {
        const selected = items.find(i => i.id === itemId);
        if (selected && count > 0) {
            setAmount(selected.price * count);
        }
    }, [count, itemId, items]);

    const handleSubmit = async () => {
        try {
            const beginRes = await fetch("/begin", { method: "POST" });
            const beginData = await beginRes.json();
            const txnId = beginData.transaction_id;

            const prepareRes = await fetch("/prepare", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    transaction_id: txnId,
                    products: [{ product_id: itemId, amount: count }]
                }),
            });

            const prepareData = await prepareRes.json();

            setResult({
                success: prepareRes.ok,
                txnId,
                message: prepareData.message || ""
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
                        <select
                            value={itemId}
                            onChange={e => setItemId(e.target.value)}
                        >
                            <option value="" disabled>請選擇商品</option>
                            {items.map((itm, idx) => (
                                <option key={idx} value={itm.id}>{itm.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label>數量</label>
                        <input
                            type="number"
                            value={count}
                            min={1}
                            onChange={e => setCount(Number(e.target.value))}
                            disabled={!itemId}
                        />
                    </div>
                    <div className="form-group">
                        <label>金額</label>
                        <input type="number" value={amount} disabled />
                    </div>
                    <button
                        className="submit-btn"
                        onClick={handleSubmit}
                        disabled={!itemId || count <= 0}
                    >
                        🔍
                    </button>
                </div>
            </div>

            {result && result.success && (
                <div className="result-block">
                    <p>✅ 預備完成</p>
                    <p>- Transaction ID: {result.txnId}</p>
                    <p>- 訊息：{result.message}</p>
                    <p>- 接下來請到狀態頁進行 commit 或 rollback。</p>
                </div>
            )}
            {result && !result.success && (
                <div className="result-block error">❌ 發生錯誤，請稍後再試。</div>
            )}
        </div>
    );
}

export default CreatePage;