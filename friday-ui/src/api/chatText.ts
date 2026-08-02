import { API_ENDPOINTS } from './config.js';

/**
 * Calls the text-only chat endpoint (/api/chat/text) which does LLM-only processing.
 * Connected to backend FastAPI server via centralized API_ENDPOINTS.
 */
export async function fetchChatText(text: string, silenceTts: boolean = false): Promise<{ reply: string; action: string; silence_tts?: boolean }> {
  try {
    const res = await fetch(API_ENDPOINTS.chatText, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, silence_tts: silenceTts }),
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