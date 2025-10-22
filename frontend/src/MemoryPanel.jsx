import React, { useState, useEffect } from "react";
import {
  listMemories,
  addMemory,
  editMemory,
  deleteMemory,
  listDocs,
  deleteDoc,
  uploadDoc,
} from "./api";

/** --- Helper: safely turn any value into printable string --- */
function safeText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function SimpleEditor({ value, onSave, onCancel, disabled }) {
  const [v, setV] = useState(value || "");
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input
        value={v}
        onChange={(e) => setV(e.target.value)}
        style={{ flex: 1, padding: 6 }}
        disabled={disabled}
      />
      <button onClick={() => onSave(v)} disabled={disabled}>
        Save
      </button>
      <button onClick={onCancel} disabled={disabled}>
        Cancel
      </button>
    </div>
  );
}

function Collapsible({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: 6 }}>
      <div
        style={{
          cursor: "pointer",
          fontWeight: "bold",
          display: "flex",
          justifyContent: "space-between",
        }}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{safeText(title)}</span>
        <span>{open ? "▼" : "▶"}</span>
      </div>
      {open && <div style={{ paddingLeft: 12, marginTop: 4 }}>{children}</div>}
    </div>
  );
}

export default function MemoryPanel() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("memories");
  const [loading, setLoading] = useState(false);
  const [memories, setMemories] = useState([]);
  const [docs, setDocs] = useState({});
  const [adding, setAdding] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    refreshAll();
  }, []);

  async function refreshAll() {
    setLoading(true);
    try {
      const mems = await listMemories();
      const facts = (Array.isArray(mems?.facts) ? mems.facts : []).map(
        (doc) => doc.page_content || doc.content || JSON.stringify(doc)
      );
      setMemories(facts);
    } catch (e) {
      console.warn("listMemories failed", e);
      setMemories([]);
    }

    try {
      const d = await listDocs();
      const docsArray = Array.isArray(d?.docs) ? d.docs : [];
      const grouped = {};
      docsArray.forEach((chunk) => {
        const fileName =
          chunk.filename || chunk.metadata?.filename || chunk.metadata?.source || "Unknown";
        const content = safeText(chunk.content || chunk.page_content || chunk.text || chunk);
        if (!grouped[fileName]) grouped[fileName] = [];
        grouped[fileName].push({ content, fileName });
      });
      setDocs(grouped);
    } catch (e) {
      console.warn("listDocs failed", e);
      setDocs({});
    }
    setLoading(false);
  }

  async function handleAddMemory(text) {
    if (submitting) return;
    setSubmitting(true);
    try {
      const res = await addMemory(text);
      if (res.added === 0) {
        alert("Failed to add memory: " + (res.reason || "Unknown"));
        return;
      }
      setAdding(false);
      await refreshAll();
    } catch (e) {
      alert("Failed to add memory: " + e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleEditMemory(old_text, new_text) {
    if (submitting) return;
    setSubmitting(true);
    try {
      const res = await editMemory(old_text, new_text);
      if (!res.edited) {
        alert("Failed to edit memory: " + (res.reason || "Unknown"));
        return;
      }
      setEditingItem(null);
      await refreshAll();
    } catch (e) {
      alert("Failed to edit memory: " + e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteMemory(text) {
    if (!confirm("Delete this memory?")) return;
    try {
      const res = await deleteMemory(text);
      if (!res.deleted) {
        alert("Memory deletion failed: " + (res.reason || "Unknown"));
        return;
      }
      await refreshAll();
    } catch (e) {
      alert("Failed to delete memory: " + e.message);
    }
  }

  async function handleDeleteDoc(fileName) {
    if (!confirm(`Delete entire document "${fileName}"?`)) return;
    try {
      const res = await deleteDoc(fileName);
      if (!res.ok && !res.result?.deleted) {
        alert("Document deletion failed");
        return;
      }
      await refreshAll();
    } catch (e) {
      alert("Failed to delete document: " + e.message);
    }
  }


  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file); // matches backend parameter
      await uploadDoc(form);
      await refreshAll();
      alert(`File "${file.name}" uploaded successfully!`);
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          position: "fixed",
          top: 20,
          right: open ? 370 : 20,
          zIndex: 1000,
          padding: "6px 12px",
          borderRadius: 4,
          background: "#333",
          color: "#fff",
          border: "none",
          cursor: "pointer",
        }}
      >
        {open ? "Close Knowledge" : "Open Knowledge"}
      </button>

      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          width: 360,
          height: "100%",
          background: "#fff",
          borderLeft: "1px solid #ddd",
          padding: 12,
          overflowY: "auto",
          transform: `translateX(${open ? "0" : "100%"})`,
          transition: "transform 0.3s ease",
          zIndex: 999,
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

        {loading && <p>Loading...</p>}

        {tab === "memories" && (
          <>
            {adding && (
              <div style={{ marginBottom: 12 }}>
                <h4>Add memory</h4>
                <SimpleEditor
                  value=""
                  onSave={(v) => handleAddMemory(v)}
                  onCancel={() => setAdding(false)}
                  disabled={submitting}
                />
              </div>
            )}

            {editingItem && (
              <div style={{ marginBottom: 12 }}>
                <h4>Edit</h4>
                <SimpleEditor
                  value={editingItem.value}
                  onSave={(v) => handleEditMemory(editingItem.value, v)}
                  onCancel={() => setEditingItem(null)}
                  disabled={submitting}
                />
              </div>
            )}

            {memories?.length > 0 ? (
              memories.map((m, i) => (
                <div
                  key={i}
                  style={{
                    marginBottom: 6,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span>{safeText(m)}</span>
                  <div>
                    <button
                      onClick={() =>
                        setEditingItem({ type: "memory", value: m })
                      }
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteMemory(m)}
                      style={{ marginLeft: 6 }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: "#666" }}>No memories yet.</p>
            )}

            {!adding && !editingItem && (
              <div style={{ marginTop: 12 }}>
                <button onClick={() => setAdding(true)}>+ Add</button>
              </div>
            )}
          </>
        )}

        {tab === "docs" && (
          <>
            <div style={{ marginBottom: 12 }}>
              <h4>Upload document</h4>
              <input
                type="file"
                accept=".txt,.pdf,.docx"
                onChange={handleUpload}
                disabled={uploading}
              />
            </div>

            {docs && Object.keys(docs).length > 0 ? (
              Object.keys(docs).map((file) => (
                <Collapsible
                  key={file}
                  title={file === "Unknown" ? "Unnamed Document" : file}
                >
                  <button
                    onClick={() => handleDeleteDoc(file)}
                    style={{ marginBottom: 8 }}
                  >
                    Delete entire document
                  </button>
                  {docs[file].map((chunk, idx) => (
                    <Collapsible key={idx} title={`Chunk ${idx + 1}`}>
                      <pre
                        style={{
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {safeText(chunk.content)}
                      </pre>
                    </Collapsible>
                  ))}
                </Collapsible>
              ))
            ) : (
              <p style={{ color: "#666" }}>No docs indexed.</p>
            )}
          </>
        )}
      </div>
    </>
  );
}
