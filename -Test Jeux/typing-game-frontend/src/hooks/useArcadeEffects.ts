import { useEffect } from 'react';

/**
 * Listens for the custom 'word-correct' event and shakes the whole page (app container)
 * for a brief moment to celebrate correct word completion.
 */
export function useArcadeEffects() {
  useEffect(() => {
    const onWordCorrect = () => {
      const app = document.querySelector('.app');
      document.body.classList.add('shake');
      if (app) app.classList.add('shake');
      window.setTimeout(() => {
        document.body.classList.remove('shake');
        if (app) app.classList.remove('shake');
      }, 160);
    };

    const onWordInvalid = () => {
      const app = document.querySelector('.app');
      document.body.classList.add('flash');
      if (app) app.classList.add('flash');
      setTimeout(() => {
        document.body.classList.remove('flash');
        if (app) app.classList.remove('flash');
      }, 180);
    };

    window.addEventListener('word-correct', onWordCorrect as EventListener);
  window.addEventListener('word-invalid', onWordInvalid as EventListener);
    return () => {
      window.removeEventListener('word-correct', onWordCorrect as EventListener);
  window.removeEventListener('word-invalid', onWordInvalid as EventListener);
    };
  }, []);
}
