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

function playBeep() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'square';
    o.frequency.value = 880; // A5
    g.gain.value = 0.07;
    o.connect(g);
    g.connect(ctx.destination);
    o.start();
    // Quick pitch slide down for arcade feel
    const now = ctx.currentTime;
    o.frequency.setValueAtTime(880, now);
    o.frequency.exponentialRampToValueAtTime(440, now + 0.12);
    g.gain.exponentialRampToValueAtTime(0.0001, now + 0.14);
    o.stop(now + 0.16);
  } catch {}
}

function playError() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'sawtooth';
    o.frequency.value = 180; // low buzz
    g.gain.value = 0.06;
    o.connect(g);
    g.connect(ctx.destination);
    const now = ctx.currentTime;
    o.start();
    o.frequency.exponentialRampToValueAtTime(120, now + 0.12);
    g.gain.exponentialRampToValueAtTime(0.0001, now + 0.14);
    o.stop(now + 0.16);
  } catch {}
}
