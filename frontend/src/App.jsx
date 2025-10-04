import React, { useState, useEffect } from "react";
import { createSession, sendChat, fetchHistory } from "./api";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Create or restore session
  useEffect(() => {
    const existing = localStorage.getItem("session_id");
    if (existing) {
      setSessionId(existing);
      // Optionally load history
      fetchHistory(existing)
        .then((data) => {
          if (data.messages) {
            setMessages(
              data.messages.map((m) => ({
                from: m.role === "user" ? "user" : "assistant",
                text: m.content,
              }))
            );
          }
        })
        .catch((e) => console.warn("Failed to fetch history", e));
    } else {
      createSession()
        .then((data) => {
          localStorage.setItem("session_id", data.session_id);
          setSessionId(data.session_id);
        })
        .catch((e) => console.error("Failed to create session", e));
    }
  }, []);

  async function handleSend() {
    if (!input.trim() || !sessionId) return;
    const userMsg = { role: "user", content: input };
    setMessages((m) => [...m, { from: "user", text: input }]);
    setInput("");
    setLoading(true);
    try {
      const res = await sendChat(sessionId, [userMsg]);
      const reply = res.reply?.content ?? "No reply";
      setMessages((m) => [...m, { from: "assistant", text: reply }]);
    } catch (err) {
      setMessages((m) => [...m, { from: "system", text: "Error: " + err.message }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ margin: 20, fontFamily: "sans-serif" }}>
      <h1>AI Copilot (with Sessions)</h1>
      <p>Session ID: {sessionId || "(loading...)"}</p>
      <div style={{ border: "1px solid #ddd", padding: 10, minHeight: 200, marginBottom: 10 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ margin: 6, textAlign: m.from === "user" ? "right" : "left" }}>
            <b>{m.from}:</b> <span>{m.text}</span>
          </div>
        ))}
      </div>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        rows={4}
        style={{ width: "100%" }}
        disabled={loading}
      />
      <button onClick={handleSend} disabled={loading || !sessionId} style={{ marginTop: 8 }}>
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
}
