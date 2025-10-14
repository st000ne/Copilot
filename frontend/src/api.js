const API_URL = "http://127.0.0.1:8000"; // adjust if needed

// --- Session / Chat ---
export async function createSession() {
  const res = await fetch(`${API_URL}/session`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function sendChat(sessionId, messages) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, messages }),
  });
  if (!res.ok) throw new Error("Failed to send chat");
  return res.json();
}

export async function fetchSession(sessionId) {
  const res = await fetch(`${API_URL}/session/${sessionId}/history`);
  if (!res.ok) throw new Error("Failed to fetch session history");
  return res.json();
}

export async function fetchSessions() {
  const res = await fetch(`${API_URL}/sessions`);
  if (!res.ok) throw new Error("Failed to list sessions");
  return res.json();
}

export async function renameSession(sessionId, newName) {
  const res = await fetch(`${API_URL}/session/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: newName }),
  });
  if (!res.ok) throw new Error("Failed to rename session");
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${API_URL}/session/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}

export async function editAndRegenerateMessage(id, newText) {
  const res = await fetch(
    `${API_URL}/message/${id}/edit?content=${encodeURIComponent(newText)}`,
    { method: "PATCH" }
  );
  if (!res.ok) throw new Error("Failed to edit & regenerate");
  return res.json();
}

export async function continueChat(sessionId) {
  const res = await fetch(`${API_URL}/session/${sessionId}/continue`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to continue chat");
  return res.json();
}

// --- Memory (facts only now) ---
export async function listMemories() {
  const res = await fetch(`${API_URL}/memory/list`);
  if (!res.ok) throw new Error("Failed to list memories");
  return res.json();
}

export async function addMemory(text) {
  const res = await fetch(`${API_URL}/memory/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to add memory");
  return res.json();
}

export async function editMemory(old_text, new_text) {
  const res = await fetch(`${API_URL}/memory/edit`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_text, new_text }),
  });
  if (!res.ok) throw new Error("Failed to edit memory");
  return res.json();
}

export async function deleteMemory(text) {
  const res = await fetch(`${API_URL}/memory/delete`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to delete memory");
  return res.json();
}

// --- Docs ---
export async function listDocs() {
  const res = await fetch(`${API_URL}/docs/list`);
  if (!res.ok) throw new Error("Failed to list docs");
  return res.json();
}

export async function addDoc(text) {
  const res = await fetch(`${API_URL}/docs/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to add doc");
  return res.json();
}

export async function editDoc(old_text, new_text) {
  const res = await fetch(`${API_URL}/docs/edit`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_text, new_text }),
  });
  if (!res.ok) throw new Error("Failed to edit doc");
  return res.json();
}

export async function deleteDoc(text) {
  const res = await fetch(`${API_URL}/docs/delete`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to delete doc");
  return res.json();
}
