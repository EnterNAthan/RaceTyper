interface GameState {
    targetPhrase: string;
    currentInput: string;
    correctCount: number;
    incorrectCount: number;
    attempts: number;
    accuracy: number;
    startTime: Date | null;
    endTime: Date | null;
}

interface TypingGameState {
    targetPhrase: string;
    userInput: string;
    progress: number;
    attempts: number;
    accuracy: number;
    timeTaken: number;
    isGameActive: boolean;
    startTime: number | null;
    wordsCompleted?: number;
    isCompleted?: boolean;
}

interface PlayerStats {
    attempts: number;
    accuracy: number;
    timeTaken: number; // in seconds
}

export type { GameState, TypingGameState, PlayerStats };