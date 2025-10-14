import React, { useState, useEffect } from "react";
import {
  listMemories,
  addMemory,
  editMemory,
  deleteMemory,
  listDocs,
  addDoc,
  editDoc,
  deleteDoc,
} from "./api";

function SimpleEditor({ value, onSave, onCancel }) {
  const [v, setV] = useState(value || "");
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input
        value={v}
        onChange={(e) => setV(e.target.value)}
        style={{ flex: 1, padding: 6 }}
      />
      <button onClick={() => onSave(v)}>Save</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  );
}

export default function MemoryPanel() {
  const [tab, setTab] = useState("memories");
  const [loading, setLoading] = useState(false);
  const [memories, setMemories] = useState([]);
  const [docs, setDocs] = useState([]);
  const [adding, setAdding] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  useEffect(() => {
    refreshAll();
  }, []);

  async function refreshAll() {
    setLoading(true);
    try {
      const mems = await listMemories();
      setMemories(Array.isArray(mems?.facts) ? mems.facts : []);
    } catch (e) {
      console.warn("listMemories failed", e);
      setMemories([]);
    }

    try {
      const d = await listDocs();
      // ✅ FIX: Extract docs array properly
      setDocs(Array.isArray(d?.docs) ? d.docs : []);
    } catch (e) {
      console.warn("listDocs failed", e);
      setDocs([]);
    }

    setLoading(false);
  }

  async function handleAddMemory(text) {
    try {
      await addMemory(text);
      setAdding(false);
      await refreshAll();
    } catch (e) {
      alert("Failed to add memory: " + e.message);
    }
  }

  async function handleEditMemory(old_text, new_text) {
    try {
      await editMemory(old_text, new_text);
      setEditingItem(null);
      await refreshAll();
    } catch (e) {
      alert("Failed to edit memory: " + e.message);
    }
  }

  async function handleDeleteMemory(text) {
    if (!confirm("Delete this memory?")) return;
    try {
      await deleteMemory(text);
      await refreshAll();
    } catch (e) {
      alert("Failed to delete memory: " + e.message);
    }
  }

  async function handleAddDoc(text) {
    try {
      await addDoc(text);
      setAdding(false);
      await refreshAll();
    } catch (e) {
      alert("Failed to add doc: " + e.message);
    }
  }

  async function handleEditDoc(old_text, new_text) {
    try {
      await editDoc(old_text, new_text);
      setEditingItem(null);
      await refreshAll();
    } catch (e) {
      alert("Failed to edit doc: " + e.message);
    }
  }

  async function handleDeleteDoc(text) {
    if (!confirm("Delete this doc chunk?")) return;
    try {
      await deleteDoc(text);
      await refreshAll();
    } catch (e) {
      alert("Failed to delete doc: " + e.message);
    }
  }

  function getDisplayText(item) {
    if (typeof item === "string") return item;
    if (item?.content) return item.content;
    if (item?.text) return item.text;
    return JSON.stringify(item);
  }

  return (
    <div
      style={{
        width: 360,
        borderLeft: "1px solid #ddd",
        padding: 12,
        overflowY: "auto",
        background: "#fff",
      }}
    >
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button
          onClick={() => setTab("memories")}
          style={{ fontWeight: tab === "memories" ? "bold" : "normal" }}
        >
          Memories
        </button>
        <button
          onClick={() => setTab("docs")}
          style={{ fontWeight: tab === "docs" ? "bold" : "normal" }}
        >
          Docs
        </button>
        <button onClick={refreshAll} style={{ marginLeft: "auto" }}>
          Refresh
        </button>
      </div>

      {adding ? (
        <div style={{ marginBottom: 12 }}>
          {tab === "memories" && (
            <>
              <h4>Add memory</h4>
              <SimpleEditor
                value=""
                onSave={(v) => handleAddMemory(v)}
                onCancel={() => setAdding(false)}
              />
            </>
          )}
          {tab === "docs" && (
            <>
              <h4>Add doc text</h4>
              <SimpleEditor
                value=""
                onSave={(v) => handleAddDoc(v)}
                onCancel={() => setAdding(false)}
              />
              <p style={{ fontSize: 12, color: "#666" }}>
                Long text will be split into chunks and indexed.
              </p>
            </>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button onClick={() => setAdding(true)}>+ Add</button>
          <button onClick={refreshAll}>Refresh</button>
        </div>
      )}

      {editingItem && (
        <div style={{ marginBottom: 12 }}>
          <h4>Edit</h4>
          <SimpleEditor
            value={getDisplayText(editingItem.old)}
            onSave={(v) => {
              if (editingItem.type === "memory")
                handleEditMemory(editingItem.old, v);
              else if (editingItem.type === "doc")
                handleEditDoc(editingItem.old, v);
            }}
            onCancel={() => setEditingItem(null)}
          />
        </div>
      )}

      {loading && <p>Loading...</p>}

      {tab === "memories" && (
        <>
          {Array.isArray(memories) && memories.length > 0 ? (
            memories.map((m, i) => {
              const text = typeof m === "string" ? m : m.content || "";
              return (
                <div key={i} style={{ marginBottom: 6 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div style={{ flex: 1 }}>{text}</div>
                    <div>
                      <button
                        onClick={() =>
                          setEditingItem({ type: "memory", old: text })
                        }
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteMemory(text)}
                        style={{ marginLeft: 6 }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <p style={{ color: "#666" }}>No memories yet.</p>
          )}
        </>
      )}

      {tab === "docs" && (
        <>
          {Array.isArray(docs) && docs.length > 0 ? (
            docs.map((d, i) => {
              const text = getDisplayText(d);
              return (
                <div key={i} style={{ marginBottom: 6 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div style={{ flex: 1 }}>{text}</div>
                    <div>
                      <button
                        onClick={() => setEditingItem({ type: "doc", old: d })}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteDoc(d)}
                        style={{ marginLeft: 6 }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <p style={{ color: "#666" }}>No docs indexed.</p>
          )}
        </>
      )}
    </div>
  );
}
