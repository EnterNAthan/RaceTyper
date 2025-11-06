import React from 'react';

interface TypingPhraseProps {
    targetPhrase: string;
    userInput: string;
}

export const TypingPhrase: React.FC<TypingPhraseProps> = ({ targetPhrase, userInput }) => {
    // Guard against unexpected non-string values
    const safeTarget = typeof targetPhrase === 'string' ? targetPhrase : '';

    const getCharacterClass = (char: string, index: number) => {
        if (index < userInput.length) {
            return char === userInput[index] ? 'correct' : 'incorrect';
        }
        return '';
    };

    return (
        <div className="typing-phrase" aria-label="Target phrase">
            {safeTarget.split('').map((char, index) => (
                <span key={index} className={getCharacterClass(char, index)}>
                    {char}
                </span>
            ))}
        </div>
    );
};

interface TypingInputProps {
    value: string;
    onChange: (v: string) => void;
    disabled?: boolean;
}

export const TypingInput: React.FC<TypingInputProps> = ({ value, onChange, disabled }) => {
    return (
        <div className="typing-input-card" onKeyDown={(e) => {
            const div = e.currentTarget;
            div.classList.add('shake');
            setTimeout(() => div.classList.remove('shake'), 120);
        }}>
            <input
                className="typing-input"
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder="Commencez à taper ici..."
                autoFocus
                disabled={disabled}
            />
        </div>
    );
};

export default TypingPhrase;