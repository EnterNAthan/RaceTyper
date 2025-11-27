export const validateInput = (input: string, target: string): { isValid: boolean; errorIndex: number | null } => {
    let isValid = true;
    let errorIndex: number | null = null;

    for (let i = 0; i < input.length; i++) {
        if (input[i] !== target[i]) {
            isValid = false;
            errorIndex = i;
            break;
        }
    }

    return { isValid, errorIndex };
};

export const isComplete = (input: string, target: string): boolean => {
    return input.length === target.length && input === target;
};