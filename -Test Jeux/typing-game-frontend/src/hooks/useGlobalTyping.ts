import { useEffect } from 'react';

type GlobalTypingOptions = {
  isGameActive: boolean;
  isCompleted: boolean;
  userInput: string;
  handleInputChange: (next: string) => void;
};

/**
 * Listens to window keydown events and forwards printable chars, space and backspace
 * to the game's input handler, so the user doesn't need to focus the text field.
 */
export function useGlobalTyping({ isGameActive, isCompleted, userInput, handleInputChange }: GlobalTypingOptions) {
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

      // Handle backspace
      if (e.key === 'Backspace') {
        if (userInput.length > 0) {
          next = userInput.slice(0, -1);
        } else {
          next = userInput;
        }
        e.preventDefault();
      }

      // Handle space
      else if (e.key === ' ' || e.code === 'Space' || e.key === 'Spacebar') {
        next = userInput + ' ';
        e.preventDefault();
      }

      // Printable characters (single-char keys)
      else if (e.key && e.key.length === 1) {
        next = userInput + e.key;
        // do not prevent default to allow potential sound shortcuts, but it's fine either way
      }

      if (next !== null) {
        handleInputChange(next);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isGameActive, isCompleted, userInput, handleInputChange]);
}

export default useGlobalTyping;
