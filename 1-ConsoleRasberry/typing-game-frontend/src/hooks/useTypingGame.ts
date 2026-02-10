import { useState, useCallback, useEffect } from 'react';
import { TypingGameState } from '../types/game';

interface UseTypingGameProps {
    targetPhrase?: string;
    onPhraseComplete?: (stats: {
        timeTaken: number;
        errorsCount: number;
        bonus: string[];
        malus: string[];
    }) => void;
}

export const useTypingGame = ({ targetPhrase = "", onPhraseComplete }: UseTypingGameProps = {}) => {
    const [state, setState] = useState<TypingGameState>({
        targetPhrase: targetPhrase,
        userInput: "",
        progress: 0,
        attempts: 0,
        accuracy: 100,
        timeTaken: 0,
        isGameActive: false,
        startTime: null,
        wordsCompleted: 0,
    });

    const [errorsCount, setErrorsCount] = useState(0);
    const [bonusWords, setBonusWords] = useState<string[]>([]);
    const [malusWords, setMalusWords] = useState<string[]>([]);

    // Update state when targetPhrase prop changes
    useEffect(() => {
        if (targetPhrase) {
            setState(prev => ({
                ...prev,
                targetPhrase: targetPhrase,
            }));
        }
    }, [targetPhrase]);

    // Extract bonus and malus words from phrase
    useEffect(() => {
        if (state.targetPhrase) {
            const bonusMatches = state.targetPhrase.match(/\^([^\^]+)\^/g);
            const malusMatches = state.targetPhrase.match(/&([^&]+)&/g);

            setBonusWords(bonusMatches ? bonusMatches.map(m => m.replace(/[\^]/g, '')) : []);
            setMalusWords(malusMatches ? malusMatches.map(m => m.replace(/[&]/g, '')) : []);
        }
    }, [state.targetPhrase]);

    const calculateAccuracy = useCallback((target: string, input: string): number => {
        if (input.length === 0) return 100;
        
        let correctChars = 0;
        for (let i = 0; i < Math.min(target.length, input.length); i++) {
            if (target[i] === input[i]) {
                correctChars++;
            }
        }
        return Math.round((correctChars / input.length) * 100);
    }, []);

    const handleInputChange = useCallback((input: string) => {
        if (!state.isGameActive) return;

        // Strip visual markers (^word^ for rainbow, &word& for alert) from target for logic
        const cleanTarget = state.targetPhrase
            .replace(/\^([^\s]+)\^/g, '$1')
            .replace(/&([^\s]+)&/g, '$1');

        // Compute locked prefix: previously validated words + trailing space
        const targetWords = cleanTarget.split(/\s+/);
        const lockedPrefix = (state.wordsCompleted && state.wordsCompleted > 0)
            ? targetWords.slice(0, state.wordsCompleted).join(' ') + ' '
            : '';

        // Prevent deleting into locked prefix (cannot erase past validated words)
        let nextInput = input;
        if (nextInput.length < lockedPrefix.length) {
            nextInput = lockedPrefix;
        }
        if (!nextInput.startsWith(lockedPrefix)) {
            // If someone tries to modify before the lock (paste/edit), restore the prefix
            nextInput = lockedPrefix + nextInput.slice(lockedPrefix.length);
        }

        // Enforce max length of current word: do not allow more letters than target word length
        const currentIndex = state.wordsCompleted ?? 0;
        const currentWord = targetWords[currentIndex] || '';
        const afterLock = nextInput.slice(lockedPrefix.length);
        // Take characters up to first space as the typed segment for the current word
        const spacePos = afterLock.indexOf(' ');
        let typedSegment = spacePos >= 0 ? afterLock.slice(0, spacePos) : afterLock;
        if (typedSegment.length > currentWord.length) {
            typedSegment = typedSegment.slice(0, currentWord.length);
            nextInput = lockedPrefix + typedSegment; // drop any extra pasted content beyond the limit
        }

        // Visual feedback on wrong letter but do not block typing
        const prev = state.userInput;
        if (nextInput.length > prev.length) {
            const nextChar = nextInput.slice(-1);
            // Do not block or flash on mere wrong letter; only feedback on validation below
            // If the next char is a space, only accept it when the current word is correct
            if (nextChar === ' ') {
                const withoutTrailing = nextInput.trimEnd();
                const completedWords = withoutTrailing.length ? withoutTrailing.split(/\s+/) : [];
                const idx = completedWords.length - 1;
                const targetWords2 = cleanTarget.split(/\s+/);
                if (idx >= 0 && completedWords[idx] !== targetWords2[idx]) {
                    // Reject this space: do not move to the next word and show validation error
                    setErrorsCount(prev => prev + 1);
                    window.dispatchEvent(new Event('word-invalid'));
                    return;
                }
            }
        }

    const progress = Math.min((nextInput.length / cleanTarget.length) * 100, 100);
        const accuracy = calculateAccuracy(cleanTarget, nextInput);
        const currentTime = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;

        setState(prev => ({
            ...prev,
            userInput: nextInput,
            progress,
            accuracy,
            timeTaken: currentTime,
        }));

        // Check if game is completed
        if (nextInput === cleanTarget) {
            const finalTime = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;
            setState(prev => ({ ...prev, isGameActive: false, isCompleted: true, timeTaken: finalTime }));

            // Call completion callback with stats
            if (onPhraseComplete) {
                onPhraseComplete({
                    timeTaken: finalTime,
                    errorsCount: errorsCount,
                    bonus: bonusWords,
                    malus: malusWords,
                });
            }
        }

        // Detect word completion only on insertion of a space (avoid firing on deletions)
        const lastChar = nextInput.slice(-1);
        const wasInsertion = nextInput.length > prev.length;
        if (wasInsertion && lastChar === ' ') {
            const wordsTyped = nextInput.trim().split(/\s+/);
            const targetWords3 = cleanTarget.split(/\s+/);
            const correctSoFar = wordsTyped.every((w, i) => w === targetWords3[i]);
            if (correctSoFar && wordsTyped.length > (state.wordsCompleted ?? 0)) {
                // increment wordsCompleted and fire event
                setState(prev => ({ ...prev, wordsCompleted: (prev.wordsCompleted ?? 0) + 1 }));
                window.dispatchEvent(new Event('word-correct'));
            }
        }
    }, [state.isGameActive, state.targetPhrase, state.startTime, state.wordsCompleted, state.userInput, calculateAccuracy, onPhraseComplete, errorsCount, bonusWords, malusWords]);

    const startGame = useCallback((overridePhrase?: string) => {
        // Start a new game, optionally with a new phrase (for round transitions)
        setErrorsCount(0);
        setState(prev => ({
            ...prev,
            targetPhrase: overridePhrase || prev.targetPhrase,
            userInput: "",
            progress: 0,
            attempts: 0,
            accuracy: 100,
            timeTaken: 0,
            isGameActive: true,
            isCompleted: false,
            startTime: Date.now(),
            wordsCompleted: 0,
        }));
    }, []);

    return {
        targetPhrase: state.targetPhrase,
        userInput: state.userInput,
        progress: state.progress,
        attempts: state.attempts,
        accuracy: state.accuracy,
        timeTaken: state.timeTaken,
        isGameActive: state.isGameActive,
        isCompleted: state.isCompleted ?? false,
        wordsCompleted: state.wordsCompleted ?? 0,
        handleInputChange,
        startGame,
    };
};