import { useEffect } from 'react';

type GlobalTypingOptions = {
  isGameActive: boolean;
  isCompleted: boolean;
  userInput: string;
  targetPhrase: string;
  wordsCompleted: number;
  handleInputChange: (next: string) => void;
};

/**
 * Listens to window keydown events and forwards printable chars, space and backspace
 * to the game's input handler, so the user doesn't need to focus the text field.
 */
export function useGlobalTyping({ isGameActive, isCompleted, userInput, targetPhrase, wordsCompleted, handleInputChange }: GlobalTypingOptions) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!isGameActive || isCompleted) return;

      // If the event started in an editable field, don't hijack it
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const isEditable =
        (target && (target as HTMLElement).isContentEditable) ||
        tag === 'input' ||
        tag === 'textarea';
      if (isEditable) return;

      // Ignore if modifier keys are pressed
      if (e.ctrlKey || e.altKey || e.metaKey) return;

      let next: string | null = null;

      // Compute locked prefix length from target phrase and wordsCompleted
      const cleanTarget = targetPhrase
        .replace(/\^([^\s]+)\^/g, '$1')
        .replace(/&([^\s]+)&/g, '$1');
      const targetWords = cleanTarget.split(/\s+/);
      const lockedPrefixLength = wordsCompleted > 0 ? targetWords.slice(0, wordsCompleted).join(' ').length + 1 : 0;

      // Handle backspace
      if (e.key === 'Backspace') {
        if (userInput.length > lockedPrefixLength) {
          next = userInput.slice(0, -1);
        } else {
          next = userInput; // clamp, do nothing if at or before lock
        }
        e.preventDefault();
      }

      // Printable characters (single-char keys, including space)
      else if (e.key && e.key.length === 1) {
        next = userInput + e.key;
        e.preventDefault();
      }
      else if (e.key === ' ' || e.code === 'Space' || e.key === 'Spacebar') {
        // Space is still forwarded but auto-validate in useTypingGame handles word advance
        next = userInput + ' ';
        e.preventDefault();
      }

      if (next !== null) {
        handleInputChange(next);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isGameActive, isCompleted, userInput, targetPhrase, wordsCompleted, handleInputChange]);
}

export default useGlobalTyping;
