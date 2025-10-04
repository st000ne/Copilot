import React, { useState, useEffect } from "react";
import Sidebar from "./Sidebar";
import { createSession, sendChat, fetchSession } from "./api";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Load or create session
  useEffect(() => {
    const existing = localStorage.getItem("session_id");
    if (existing) {
      setSessionId(existing);
      fetchSession(existing)
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
        .catch(() => {
          localStorage.removeItem("session_id");
          createNewSession();
        });
    } else {
      createNewSession();
    }
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    fetchSession(sessionId)
      .then((data) => {
        if (data.messages) {
          setMessages(
            data.messages.map((m) => ({
              from: m.role === "user" ? "user" : "assistant",
              text: m.content,
            }))
          );
        } else {
          setMessages([]);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch session", err);
        setMessages([]);
      });
  }, [sessionId]);

  async function createNewSession() {
    try {
      const data = await createSession();
      localStorage.setItem("session_id", data.session_id);
      setSessionId(data.session_id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create session", e);
    }
  }

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
    <div style={{ display: "flex", height: "100vh", fontFamily: "sans-serif" }}>
      {/* Sidebar */}
      <Sidebar currentSessionId={sessionId} onSelectSession={(id) => setSessionId(id)} />

      {/* Chat Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: 20, backgroundColor: "gray" }}>
        <h1 style={{ marginBottom: 10 }}>AI Copilot</h1>
        <p style={{ fontSize: "0.9em", color: "black" }}>
          Session ID: {sessionId || "(loading...)"}
        </p>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            border: "1px solid #ddd",
            borderRadius: 6,
            padding: 10,
            overflowY: "auto",
            marginBottom: 10,
            background: "#fafafa",
          }}
        >
          {messages.length === 0 ? (
            <p style={{ color: "#999" }}>No messages yet.</p>
          ) : (
            messages.map((m, i) => (
              <div
                key={i}
                style={{
                  margin: "6px 0",
                  textAlign: m.from === "user" ? "right" : "left",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    padding: "8px 12px",
                    borderRadius: 12,
                    background: m.from === "user" ? "#444" : "#ddd",
                    color: m.from === "user" ? "#fff" : "#000",
                    maxWidth: "70%",
                    wordWrap: "break-word",
                  }}
                >
                  {m.text}
                </span>
              </div>
            ))
          )}
        </div>

        {/* Input */}
        <div style={{ display: "flex" }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={2}
            style={{
              flex: 1,
              resize: "none",
              padding: 10,
              borderRadius: 6,
              border: "1px solid #ccc",
            }}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !sessionId}
            style={{
              marginLeft: 8,
              padding: "10px 16px",
              background: "#333",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
