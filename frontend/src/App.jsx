import React, { useState } from "react";
import { sendChat } from "./api";

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input };
    setMessages(m => [...m, { from: "user", text: input }]);
    setInput("");
    setLoading(true);
    try {
      const res = await sendChat([userMsg]);
      const reply = res.reply?.content ?? "No reply";
      setMessages(m => [...m, { from: "assistant", text: reply }]);
    } catch (err) {
      setMessages(m => [...m, { from: "system", text: "Error: " + err.message }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ margin: 20, fontFamily: "sans-serif" }}>
      <h1>AI Copilot (MVP)</h1>
      <div style={{ border: "1px solid #ddd", padding: 10, minHeight: 200, marginBottom: 10 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ margin: 6, textAlign: m.from === "user" ? "right" : "left" }}>
            <b>{m.from}:</b> <span>{m.text}</span>
          </div>
        ))}
      </div>
      <textarea value={input} onChange={e => setInput(e.target.value)} rows={4} style={{ width: "100%" }} />
      <button onClick={handleSend} disabled={loading} style={{ marginTop: 8 }}>
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
}
