const API_URL = "http://127.0.0.1:8000"; // adjust if needed

export async function createSession() {
  const res = await fetch(`${API_URL}/session`, {
    method: "POST",
  });
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
  const res = await fetch(`${API_URL}/session/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}
