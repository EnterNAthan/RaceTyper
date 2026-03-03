import { useEffect, useState } from 'react';

/**
 * Shows a transient "Good!" overlay and plays a short arcade beep whenever
 * a 'word-correct' custom event is dispatched (see useTypingGame).
 */
export function useWordFeedback() {
  const [showGood, setShowGood] = useState(false);
  const [showBad, setShowBad] = useState(false);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const onWordCorrect = () => {
      setCount(c => c + 1);
      setShowGood(true);
      playBeep();
      const t = setTimeout(() => setShowGood(false), 500);
      return () => clearTimeout(t);
    };

    const onWordInvalid = () => {
      setShowBad(true);
      playError();
      const t = setTimeout(() => setShowBad(false), 500);
      return () => clearTimeout(t);
    };

    window.addEventListener('word-correct', onWordCorrect as EventListener);
    window.addEventListener('word-invalid', onWordInvalid as EventListener);
    return () => {
      window.removeEventListener('word-correct', onWordCorrect as EventListener);
      window.removeEventListener('word-invalid', onWordInvalid as EventListener);
    };
  }, []);

  return { showGood, showBad, count };
}

// Reuse a single AudioContext for all sounds (creating new ones is expensive on Pi)
let sharedAudioCtx: AudioContext | null = null;
function getAudioCtx(): AudioContext {
  if (!sharedAudioCtx || sharedAudioCtx.state === 'closed') {
    sharedAudioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  }
  if (sharedAudioCtx.state === 'suspended') {
    sharedAudioCtx.resume();
  }
  return sharedAudioCtx;
}

function playBeep() {
  try {
    const ctx = getAudioCtx();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'square';
    o.frequency.value = 880;
    g.gain.value = 0.07;
    o.connect(g);
    g.connect(ctx.destination);
    const now = ctx.currentTime;
    o.start(now);
    o.frequency.setValueAtTime(880, now);
    o.frequency.exponentialRampToValueAtTime(440, now + 0.12);
    g.gain.exponentialRampToValueAtTime(0.0001, now + 0.14);
    o.stop(now + 0.16);
  } catch {}
}

function playError() {
  try {
    const ctx = getAudioCtx();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'sawtooth';
    o.frequency.value = 180;
    g.gain.value = 0.06;
    o.connect(g);
    g.connect(ctx.destination);
    const now = ctx.currentTime;
    o.start(now);
    o.frequency.exponentialRampToValueAtTime(120, now + 0.12);
    g.gain.exponentialRampToValueAtTime(0.0001, now + 0.14);
    o.stop(now + 0.16);
  } catch {}
}
