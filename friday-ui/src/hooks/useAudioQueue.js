import { useCallback, useEffect, useRef, useState } from 'react';
import { createAudioPlayer } from '../utils/audioPlayer';

export function useAudioQueue({ onStart, onEnd, onError, audioContextRef } = {}) {
  const playerRef = useRef(null);
  const queueRef = useRef([]);
  // busyRef (not React state) is the source of truth for "is a clip playing".
  // Using React state here caused a stale-closure bug where enqueue() could fire
  // play() twice concurrently — the second interrupted the first and produced
  // "play() interrupted by a call to pause()" AbortErrors / choppy audio.
  const busyRef = useRef(false);
  const [isPlaying, setIsPlaying] = useState(false);

  // Keep the latest callbacks in refs so processQueue/enqueue stay stable and
  // are never rebuilt on every render (which also broke the stale-closure guard).
  const onStartRef = useRef(onStart);
  const onEndRef = useRef(onEnd);
  const onErrorRef = useRef(onError);
  onStartRef.current = onStart;
  onEndRef.current = onEnd;
  onErrorRef.current = onError;

  const processQueue = useCallback(() => {
    if (queueRef.current.length === 0) {
      busyRef.current = false;
      setIsPlaying(false);
      onEndRef.current?.();
      return;
    }

    const nextItem = queueRef.current.shift();
    const player = playerRef.current;
    if (!player) {
      onErrorRef.current?.(new Error('Audio player not initialized.'));
      return;
    }

    busyRef.current = true;
    setIsPlaying(true);
    onStartRef.current?.();
    player.load(nextItem.url);
    player.play().catch((error) => {
      console.warn('Audio playback failed:', error);
      onErrorRef.current?.(error);
      processQueue();
    });
  }, []);

  const enqueue = useCallback(
    (url) => {
      queueRef.current.push({ url });
      if (!busyRef.current) {
        processQueue();
      }
    },
    [processQueue],
  );

  const clear = useCallback(() => {
    queueRef.current = [];
  }, []);

  const stop = useCallback(() => {
    clear();
    const player = playerRef.current;
    if (player) {
      player.stop();
    }
    busyRef.current = false;
    setIsPlaying(false);
    onEndRef.current?.();
  }, [clear]);

  useEffect(() => {
    playerRef.current = createAudioPlayer({
      audioContextRef,
      onEnded: () => {
        processQueue();
      },
      onError: (error) => {
        console.warn('Audio player error:', error);
        onErrorRef.current?.(error);
        processQueue();
      },
    });

    return () => {
      playerRef.current?.cleanup();
      playerRef.current = null;
    };
  }, [processQueue]);

  return {
    enqueue,
    playNext: processQueue,
    clear,
    stop,
    isPlaying,
  };
}
