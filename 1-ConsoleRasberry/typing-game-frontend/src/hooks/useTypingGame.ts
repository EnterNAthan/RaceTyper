import { useState, useCallback, useEffect, useRef } from 'react';
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
    // Ref pour lire la valeur courante des erreurs de façon synchrone dans handleInputChange
    const errorsRef = useRef(0);
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

    // Formule standard WPM : accuracy = nb_cibles / (nb_cibles + nb_erreurs)
    // Chaque erreur est comptée comme une frappe incorrecte supplémentaire.
    const calculateAccuracy = useCallback((target: string, currentErrors: number): number => {
        if (currentErrors === 0) return 100;
        return Math.max(0, Math.round(target.length / (target.length + currentErrors) * 100));
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

        // Check if the newly typed character is wrong → reset current word
        const prev = state.userInput;
        if (nextInput.length > prev.length) {
            const newCharIndex = nextInput.length - 1;
            const expectedChar = cleanTarget[newCharIndex];
            const typedChar = nextInput[newCharIndex];

            // Space key: reject if current word isn't correct
            if (typedChar === ' ') {
                const withoutTrailing = nextInput.trimEnd();
                const completedWords = withoutTrailing.length ? withoutTrailing.split(/\s+/) : [];
                const idx = completedWords.length - 1;
                if (idx >= 0 && completedWords[idx] !== targetWords[idx]) {
                    errorsRef.current += 1;
                    setErrorsCount(errorsRef.current);
                    window.dispatchEvent(new Event('word-invalid'));
                    return;
                }
            }
            // Wrong letter: reset the current word
            else if (expectedChar !== undefined && typedChar !== expectedChar) {
                errorsRef.current += 1;
                setErrorsCount(errorsRef.current);
                window.dispatchEvent(new Event('word-invalid'));
                // Reset input back to the locked prefix (erase current word progress)
                nextInput = lockedPrefix;
            }
        }

        // Auto-validate: if current word is fully and correctly typed, auto-advance
        const afterLockNow = nextInput.slice(lockedPrefix.length);
        const isLastWord = currentIndex === targetWords.length - 1;
        if (afterLockNow.length > 0 && afterLockNow === currentWord && !isLastWord) {
            // Append space to move to the next word automatically
            nextInput = nextInput + ' ';
            const newWordsCompleted = (state.wordsCompleted ?? 0) + 1;
            const progress = Math.min((nextInput.length / cleanTarget.length) * 100, 100);
            const accuracy = calculateAccuracy(cleanTarget, errorsRef.current);
            const currentTime = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;

            setState(prev => ({
                ...prev,
                userInput: nextInput,
                progress,
                accuracy,
                timeTaken: currentTime,
                wordsCompleted: newWordsCompleted,
            }));
            window.dispatchEvent(new Event('word-correct'));
            return;
        }

        const progress = Math.min((nextInput.length / cleanTarget.length) * 100, 100);
        const accuracy = calculateAccuracy(cleanTarget, errorsRef.current);
        const currentTime = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;

        setState(prev => ({
            ...prev,
            userInput: nextInput,
            progress,
            accuracy,
            timeTaken: currentTime,
        }));

        // Check if game is completed (last word fully typed)
        if (nextInput === cleanTarget) {
            const finalTime = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;
            setState(prev => ({ ...prev, isGameActive: false, isCompleted: true, timeTaken: finalTime }));
            window.dispatchEvent(new Event('word-correct'));

            if (onPhraseComplete) {
                onPhraseComplete({
                    timeTaken: finalTime,
                    errorsCount: errorsCount,
                    bonus: bonusWords,
                    malus: malusWords,
                });
            }
        }
    }, [state.isGameActive, state.targetPhrase, state.startTime, state.wordsCompleted, state.userInput, calculateAccuracy, onPhraseComplete, bonusWords, malusWords]);

    const startGame = useCallback((overridePhrase?: string) => {
        // Start a new game, optionally with a new phrase (for round transitions)
        errorsRef.current = 0;
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