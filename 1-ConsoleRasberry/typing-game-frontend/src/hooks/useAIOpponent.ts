import { useEffect, useRef, useState } from 'react';

// AI Difficulty levels with different characteristics
type AIDifficulty = 'beginner' | 'intermediate' | 'expert' | 'impossible'| 'debile';

interface DifficultySettings {
  name: string;
  typingDelay: number;    // ms per character (lower = faster)
  errorRate: number;      // 0-1 probability of making an error
  description: string;
}

const DIFFICULTY_SETTINGS: Record<AIDifficulty, DifficultySettings> = {
  beginner: {
    name: 'Beginner',
    typingDelay: 400,
    errorRate: 0.20,
    description: 'Slow with some errors'
  },
  intermediate: {
    name: 'Intermediate', 
    typingDelay: 150,
    errorRate: 0.08,
    description: 'Normal speed, fairly precise'
  },
  expert: {
    name: 'Expert',
    typingDelay: 80,
    errorRate: 0.05,
    description: 'Fast and precise'
  },
  impossible: {
    name: 'Impossible',
    typingDelay: 40,
    errorRate: 0.02,
    description: 'Superhuman speed'
  },
  debile: {
    name: 'Training',
    typingDelay: 80,
    errorRate: 0.70,
    description: 'Fast but inaccurate'
  }
};

type UseAIOpponentOptions = {
  targetPhrase: string;
  isGameActive: boolean;
  isCompleted: boolean;
  aiEnabled: boolean;
  difficulty?: AIDifficulty;
};

// Small helper to clean markers like in useTypingGame
function cleanTarget(phrase: string) {
  return phrase.replace(/\^([^\s]+)\^/g, '$1').replace(/&([^\s]+)&/g, '$1');
}

export function useAIOpponent({ targetPhrase, isGameActive, isCompleted, aiEnabled, difficulty = 'intermediate' }: UseAIOpponentOptions) {
  const [aiInput, setAiInput] = useState('');
  const [aiProgress, setAiProgress] = useState(0);
  const [aiErrors, setAiErrors] = useState(0); // Track errors made by AI
  const [aiCompleted, setAiCompleted] = useState(false); // Track if AI finished
  const [startTime, setStartTime] = useState<number | null>(null);
  const cursorRef = useRef(0);
  const runningRef = useRef(false);
  const targetRef = useRef(cleanTarget(targetPhrase));
  
  const difficultySettings = DIFFICULTY_SETTINGS[difficulty];
  
  // Calculate AI WPM (Words Per Minute)
  const calculateWPM = (): number => {
    if (!startTime || aiInput.length === 0) return 0;
    const timeElapsed = (Date.now() - startTime) / 1000 / 60; // minutes
    const wordsTyped = aiInput.length / 5; // standard: 5 chars = 1 word
    return Math.round(wordsTyped / timeElapsed);
  };

  useEffect(() => {
    targetRef.current = cleanTarget(targetPhrase);
  }, [targetPhrase]);

  useEffect(() => {
    // Reset AI when a game starts/stops or toggle changes
    if (!aiEnabled || !isGameActive) {
      setAiInput('');
      cursorRef.current = 0;
      setAiProgress(0);
      setAiErrors(0); // Reset error count
      setAiCompleted(false); // Reset completion status
      setStartTime(null);
      runningRef.current = false;
      return;
    }

    if (isCompleted) {
      runningRef.current = false;
      return;
    }

    let cancelled = false;
    runningRef.current = true;
    
    // Set start time when AI begins
    if (!startTime) {
      setStartTime(Date.now());
    }

    async function stepOnce() {
      if (cancelled || !runningRef.current) return;
      const chars = targetRef.current.split('');
      if (cursorRef.current >= chars.length) {
        // AI has completed!
        runningRef.current = false;
        setAiCompleted(true);
        setAiProgress(100);
        return;
      }

      const targetCharacter = chars[cursorRef.current];
      
      // Map the target character to its index in the backend CHARS string
      // Backend CHARS: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!"
      const BACKEND_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!";
      const targetCharIndex = BACKEND_CHARS.indexOf(targetCharacter);
      
      // If character not found in backend charset, skip this step
      if (targetCharIndex === -1) {
        console.warn(`Character '${targetCharacter}' not found in backend charset, skipping`);
        setTimeout(stepOnce, difficultySettings.typingDelay);
        return;
      }
      
      // Simulate random errors based on difficulty
      const shouldMakeError = Math.random() < difficultySettings.errorRate;
      let predictedChar = '';
      
      if (shouldMakeError) {
        // Make a random error - pick a random character from common typing mistakes
        const errorChars = 'abcdefghijklmnopqrstuvwxyz ';
        predictedChar = errorChars[Math.floor(Math.random() * errorChars.length)];
      } else {
        // Call AI for correct prediction
        try {
          // Use a runtime-configurable AI url. Frontend dev can set window.__AI_URL or the default localhost:8000
          const AI_URL = (window as any).__AI_URL || 'http://localhost:8000';
          const resp = await fetch(AI_URL + '/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ obs: targetCharIndex }),
          });
          if (!resp.ok) throw new Error('AI server error');
          const json = await resp.json();
          predictedChar = json.char ?? '';
        } catch (e) {
          // In case of network error, retry after delay
          // console.warn('AI opponent error', e);
          if (!cancelled) setTimeout(stepOnce, difficultySettings.typingDelay * 2);
          return;
        }
      }

      // Append the AI-typed char for visual purposes
      setAiInput(prev => prev + predictedChar);

      // Check if predicted char matches target char
      if (predictedChar === targetCharacter) {
        // Correct! Advance cursor
        cursorRef.current += 1;
        setAiProgress(Math.min(100, (cursorRef.current / chars.length) * 100));
        
        // Schedule next step with normal delay
        if (!cancelled) setTimeout(stepOnce, difficultySettings.typingDelay);
      } else {
        // Wrong character! Increment error count and schedule backspace + retry
        setAiErrors(prev => prev + 1);
        setTimeout(() => {
          if (cancelled) return;
          
          // Backspace: remove the wrong character from display
          setAiInput(prev => prev.slice(0, -1));
          
          // Retry the same character after a shorter delay
          setTimeout(() => {
            if (!cancelled) stepOnce();
          }, difficultySettings.typingDelay * 0.3); // Faster retry
        }, difficultySettings.typingDelay * 0.5); // Small pause before backspace
      }
    }

    // Kick off
    stepOnce();

    return () => {
      cancelled = true;
      runningRef.current = false;
    };
  }, [aiEnabled, isGameActive, isCompleted, difficulty]);

  return { aiInput, aiProgress, aiErrors, aiCompleted, difficultySettings, aiWPM: calculateWPM() };
}

export { DIFFICULTY_SETTINGS };
export type { AIDifficulty, DifficultySettings };

export default useAIOpponent;
