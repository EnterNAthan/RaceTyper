import { useEffect } from 'react';

/**
 * Plays arcade sounds and triggers a lightweight CSS flash on the body
 * (no React state / no re-render) for better performance on Raspberry Pi.
 */
export function useWordFeedback() {
  useEffect(() => {
    const onWordCorrect = () => {
      playBeep();
      document.body.classList.add('flash-good');
      setTimeout(() => document.body.classList.remove('flash-good'), 150);
    };

    const onWordInvalid = () => {
      playError();
      document.body.classList.add('flash-bad');
      setTimeout(() => document.body.classList.remove('flash-bad'), 150);
    };

    window.addEventListener('word-correct', onWordCorrect as EventListener);
    window.addEventListener('word-invalid', onWordInvalid as EventListener);
    return () => {
      window.removeEventListener('word-correct', onWordCorrect as EventListener);
      window.removeEventListener('word-invalid', onWordInvalid as EventListener);
    };
  }, []);
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
