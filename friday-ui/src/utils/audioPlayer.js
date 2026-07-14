export function createAudioPlayer({ onEnded, onError, audioContextRef } = {}) {
  const audio = new Audio();
  audio.preload = 'auto';
  let currentUrl = '';

  // Play through the gesture-unlocked AudioContext. A BufferSource on a running
  // context is never autoplay-blocked (unlike a bare <audio>.play() called after
  // an async fetch). Falls back to the <audio> element if no context is ready.
  function playViaContext(url) {
    const ctx = audioContextRef && audioContextRef.current;
    if (!ctx) return Promise.reject(new Error('No audio context available'));
    return fetch(url, { mode: 'cors' })
      .then((r) => {
        if (!r.ok) throw new Error('Audio fetch failed: ' + r.status);
        return r.arrayBuffer();
      })
      .then((buf) => ctx.decodeAudioData(buf))
      .then(
        (audioBuffer) =>
          new Promise((resolve, reject) => {
            const src = ctx.createBufferSource();
            src.buffer = audioBuffer;
            src.connect(ctx.destination);
            src.onended = () => {
              onEnded?.();
              resolve();
            };
            src.onerror = (e) => reject(e);
            src.start(0);
          }),
      );
  }

  return {
    load(url) {
      currentUrl = url;
      audio.src = url;
      audio.load();
    },
    play() {
      const url = currentUrl || audio.src;
      if (audioContextRef && audioContextRef.current) {
        return playViaContext(url).catch((err) => {
          console.warn('Web Audio playback failed, falling back to <audio>:', err);
          return audio.play();
        });
      }
      return audio.play();
    },
    stop() {
      audio.pause();
      audio.currentTime = 0;
    },
    cleanup() {
      audio.pause();
      audio.src = '';
      audio.removeAttribute('src');
      audio.remove();
    },
  };
}
