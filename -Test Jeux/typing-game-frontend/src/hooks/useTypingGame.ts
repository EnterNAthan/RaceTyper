import { useState, useCallback } from 'react';
import { TypingGameState } from '../types/game';

export const useTypingGame = () => {
    const [state, setState] = useState<TypingGameState>({
        targetPhrase: "The quick ^brown^ fox &jumps& over the lazy dog",
        userInput: "",
        progress: 0,
        attempts: 0,
        accuracy: 100,
        timeTaken: 0,
        isGameActive: false,
        startTime: null,
        wordsCompleted: 0,
    });

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

        // Visual feedback on wrong letter but do not block typing
        const prev = state.userInput;
        if (input.length > prev.length) {
            const nextChar = input.slice(-1);
            // Do not block or flash on mere wrong letter; only feedback on validation below
            // If the next char is a space, only accept it when the current word is correct
            if (nextChar === ' ') {
                const withoutTrailing = input.trimEnd();
                const completedWords = withoutTrailing.length ? withoutTrailing.split(/\s+/) : [];
                const idx = completedWords.length - 1;
                const targetWords = cleanTarget.split(/\s+/);
                if (idx >= 0 && completedWords[idx] !== targetWords[idx]) {
                    // Reject this space: do not move to the next word and show validation error
                    window.dispatchEvent(new Event('word-invalid'));
                    return;
                }
            }
        }

        const progress = Math.min((input.length / cleanTarget.length) * 100, 100);
        const accuracy = calculateAccuracy(cleanTarget, input);
        const currentTime = state.startTime ? (Date.now() - state.startTime) / 1000 : 0;

        setState(prev => ({
            ...prev,
            userInput: input,
            progress,
            accuracy,
            timeTaken: currentTime,
        }));

        // Check if game is completed
        if (input === cleanTarget) {
            setState(prev => ({ ...prev, isGameActive: false, isCompleted: true }));
        }

        // Detect word completion: last typed character is space and the word matches target so far
        const lastChar = input.slice(-1);
        if (lastChar === ' ') {
            const wordsTyped = input.trim().split(/\s+/);
            const targetWords = cleanTarget.split(/\s+/);
            const correctSoFar = wordsTyped.every((w, i) => w === targetWords[i]);
            if (correctSoFar && wordsTyped.length > (state.wordsCompleted ?? 0)) {
                // increment wordsCompleted and fire event
                setState(prev => ({ ...prev, wordsCompleted: (prev.wordsCompleted ?? 0) + 1 }));
                window.dispatchEvent(new Event('word-correct'));
            }
        }
    }, [state.isGameActive, state.targetPhrase, state.startTime, calculateAccuracy]);

    const startGame = useCallback(() => {
        // Start a new game using the current targetPhrase
        setState(prev => ({
            ...prev,
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