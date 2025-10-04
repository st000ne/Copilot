import React, { useEffect, useState } from "react";
import { fetchSessions, createSession, deleteSession, renameSession } from "./api";

export default function Sidebar({ currentSessionId, onSelectSession }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    refreshSessions();
  }, []);

  async function refreshSessions() {
    try {
      const data = await fetchSessions();
      setSessions(data);
    } catch (e) {
      console.error("Failed to load sessions", e);
    }
  }

  async function handleNewSession() {
    await createSession();
    refreshSessions();
  }

  async function handleDelete(id) {
    await deleteSession(id);
    refreshSessions();
  }

  async function handleRename(id) {
    const name = prompt("Enter new name:");
    if (name) {
      await renameSession(id, name);
      refreshSessions();
    }
  }

  return (
    <div
      style={{
        width: 220,
        background: "#222",
        color: "#fff",
        padding: 12,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <button
        onClick={handleNewSession}
        style={{
          marginBottom: 12,
          padding: "10px",
          background: "#444",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          cursor: "pointer",
        }}
      >
        + New Chat
      </button>

      <div style={{ flex: 1, overflowY: "auto" }}>
        {sessions.map((s) => (
          <div
            key={s.id}
            style={{
              marginBottom: 8,
              padding: 8,
              borderRadius: 6,
              background: s.id === Number(currentSessionId) ? "#555" : "#333",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              cursor: "pointer",
            }}
          >
            <span onClick={() => onSelectSession(s.id)} style={{ flex: 1 }}>
              {s.name || `Session ${s.id}`}
            </span>
            <button onClick={() => handleRename(s.id)} style={{ marginLeft: 4 }}>
              ✏️
            </button>
            <button onClick={() => handleDelete(s.id)} style={{ marginLeft: 4 }}>
              🗑️
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
