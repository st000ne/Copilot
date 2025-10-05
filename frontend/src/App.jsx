import React, { useState, useEffect } from "react";
import Sidebar from "./Sidebar";
import {
  createSession,
  sendChat,
  fetchSession,
  editAndRegenerateMessage,
  continueChat,
} from "./api";

function Message({ msg, onEdit, onContinue }) {
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(msg.text);

  const handleSave = () => {
    setEditing(false);
    onEdit(msg.id, draft);
  };

  const bubbleStyle = {
    display: "inline-block",
    padding: "8px 12px",
    borderRadius: 12,
    background: msg.from === "user" ? "#444" : "#ddd",
    color: msg.from === "user" ? "#fff" : "#000",
    maxWidth: "70%",
    wordWrap: "break-word",
  };

  return (
    <div
      style={{
        margin: "6px 0",
        textAlign: msg.from === "user" ? "right" : "left",
      }}
    >
      {editing ? (
        <>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            style={{ width: "60%" }}
          />
          <button onClick={handleSave}>💾</button>
        </>
      ) : (
        <>
          <span style={bubbleStyle}>{msg.text}</span>
          {(msg.from === "user" || msg.from === "assistant") && msg.id && (
            <button
              onClick={() => setEditing(true)}
              style={{
                marginLeft: 6,
                background: "transparent",
                border: "none",
                cursor: "pointer",
              }}
            >
              ✏️
            </button>
          )}
          {msg.from === "assistant" && (
            <button
              onClick={() => onContinue(msg)}
              style={{
                marginLeft: 6,
                background: "transparent",
                border: "none",
                cursor: "pointer",
              }}
            >
              🔁
            </button>
          )}
        </>
      )}
    </div>
  );
}

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
                id: m.id,
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
              id: m.id,
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

    // Add user message immediately
    setMessages((m) => [...m, { from: "user", text: input }]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(sessionId, [userMsg]);

      if (res.reply) {
        // Simple backend format
        setMessages((m) => [
          ...m,
          { id: res.reply.id, from: "assistant", text: res.reply.content },
        ]);
      } else if (res.messages) {
        // Full conversation response
        const newMsgs = res.messages
          .filter((msg) => msg.role !== "user")
          .map((msg) => ({
            id: msg.id,
            from: msg.role === "assistant" ? "assistant" : "system",
            text: msg.content,
          }));
        setMessages((m) => [...m, ...newMsgs]);
      }
    } catch (err) {
      console.error("Failed to send message", err);
      setMessages((m) => [
        ...m,
        { from: "system", text: "Error: " + err.message },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleEditMessage(id, newText) {
    try {
      const res = await editAndRegenerateMessage(id, newText);
      // Update edited message text
      setMessages((msgs) =>
        msgs.map((m) => (m.id === id ? { ...m, text: newText } : m))
      );
      // Append new regenerated assistant reply
      if (res.reply) {
        setMessages((msgs) => [
          ...msgs,
          {
            id: res.reply.id,
            from: "assistant",
            text: res.reply.content,
          },
        ]);
      }
    } catch (err) {
      console.error("Failed to edit and regenerate", err);
    }
  }

  async function handleContinue(msg) {
    try {
      const res = await continueChat(sessionId);
      setMessages((m) => [
        ...m,
        { id: res.id, from: "assistant", text: res.content },
      ]);
    } catch (err) {
      console.error("Failed to continue chat", err);
    }
  }

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "sans-serif" }}>
      <Sidebar
        currentSessionId={sessionId}
        onSelectSession={(id) => setSessionId(id)}
      />

      {/* Chat Area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: 20,
          backgroundColor: "gray",
        }}
      >
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
              <Message
                key={i}
                msg={m}
                onEdit={handleEditMessage}
                onContinue={handleContinue}
              />
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
