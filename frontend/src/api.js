const BACKEND = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export async function createSession() {
  const res = await fetch(`${BACKEND}/session/new`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function sendChat(sessionId, messages) {
  const res = await fetch(`${BACKEND}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, messages }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || res.statusText);
  }
  return res.json();
}

export async function fetchHistory(sessionId) {
  const res = await fetch(`${BACKEND}/session/${sessionId}/history`);
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}
