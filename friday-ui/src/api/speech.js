import { API_ENDPOINTS } from './config.js';

/**
 * Sends a recorded audio clip to the backend STT engine
 * (Groq Whisper large-v3-turbo free tier → Gemini 2.5 Flash fallback).
 * Returns the transcript string, or '' when the engine had nothing to say.
 */
export async function transcribeAudioBlob(blob, filename = 'clip.ogg') {
  const form = new FormData();
  form.append('audio', blob, filename);

  const res = await fetch(API_ENDPOINTS.speechTranscribe, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    throw new Error(`speech/transcribe ${res.status}: ${await res.text()}`);
  }

  const data = await res.json();
  return (data && data.transcript) ? String(data.transcript).trim() : '';
}
