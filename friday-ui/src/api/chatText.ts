/**
 * Calls the text-only chat endpoint (/api/chat/text) which does LLM-only processing.
 * Connected to backend FastAPI server on port 8000.
 */
export async function fetchChatText(text: string): Promise<{ reply: string; action: string }> {
  try {
    const res = await fetch('http://localhost:8000/api/chat/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`chat/text ${res.status}: ${err}`);
    }

    return await res.json();
  } catch (err) {
    console.warn('[API] chatText fallback triggered:', err);
    return {
      reply: "I'm online and ready, Boss. What are your orders?",
      action: "none"
    };
  }
}