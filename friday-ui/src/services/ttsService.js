const BACKEND_TTS_URL = '/api/speak';

export async function speak(text) {
  if (!text || typeof text !== 'string') {
    throw new Error('TTS text must be a non-empty string.');
  }

  try {
    const response = await fetch(BACKEND_TTS_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `TTS backend request to ${BACKEND_TTS_URL} failed`);
    }

    const payload = await response.json();
    if (!payload?.url) throw new Error('TTS backend did not return an audio URL.');
    const audioUrl = payload.url.startsWith('/') ? `${window.location.origin}${payload.url}` : payload.url;
    console.debug('TTS backend returned audio URL:', audioUrl);
    return audioUrl;
  } catch (err) {
    console.warn('TTS backend request failed:', BACKEND_TTS_URL, err.message || err);
    throw err;
  }
}
