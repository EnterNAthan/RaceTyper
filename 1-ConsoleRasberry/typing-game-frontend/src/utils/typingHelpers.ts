export const calculateAccuracy = (input: string, target: string): number => {
    const correctChars = input.split('').filter((char, index) => char === target[index]).length;
    return target.length > 0 ? (correctChars / target.length) * 100 : 0;
};

export const getCurrentInputState = (input: string, target: string) => {
    const currentState = {
        correct: [],
        incorrect: [],
        remaining: target.slice(input.length),
    };

    for (let i = 0; i < input.length; i++) {
        if (input[i] === target[i]) {
            currentState.correct.push(input[i]);
        } else {
            currentState.incorrect.push(input[i]);
        }
    }

    return currentState;
};