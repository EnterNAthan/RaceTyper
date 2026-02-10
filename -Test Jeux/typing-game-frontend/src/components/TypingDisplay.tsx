import React from 'react';

interface TypingPhraseProps {
    targetPhrase: string;
    userInput: string;
    wordsCompleted?: number;
    isCompleted?: boolean;
}

export const TypingPhrase: React.FC<TypingPhraseProps> = ({ targetPhrase, userInput, wordsCompleted = 0, isCompleted = false }) => {
    // Parse words with markers (^word^ for rainbow, &word& for alert)
    const rawWords = targetPhrase.split(/\s+/);
    const parsed = rawWords.map(w => {
        if (/^\^.+\^$/.test(w)) {
            return { raw: w, clean: w.slice(1, -1), type: 'rainbow' as const };
        }
        if (/^&.+&$/.test(w)) {
            return { raw: w, clean: w.slice(1, -1), type: 'alert' as const };
        }
        return { raw: w, clean: w, type: 'normal' as const };
    });

    const cleanWords = parsed.map(p => p.clean);

    if (isCompleted) {
        // Full phrase view with styling by word
        let charIndex = 0;
        const fullClean = cleanWords.join(' ');
        return (
            <div className="typing-phrase" aria-label="Phrase complète">
                {parsed.map((p, wi) => (
                    <span key={wi} className={"word word-full " + (p.type === 'rainbow' ? 'word-rainbow' : p.type === 'alert' ? 'word-alert' : '')}>
                        {p.clean.split('').map((ch, ci) => {
                            const globalIndex = charIndex + ci;
                            const typedChar = userInput[globalIndex];
                            const cls = globalIndex < userInput.length ? (typedChar === ch ? 'correct' : 'incorrect') : '';
                            return <span key={ci} className={cls}>{ch}</span>;
                        })}
                        {(() => { charIndex += p.clean.length + 1; return null; })()}
                    </span>
                ))}
            </div>
        );
    }

    const currentWordMeta = parsed[wordsCompleted];
    const previousWords = parsed.slice(0, wordsCompleted);
    const typedSegment = userInput.split(/\s+/)[wordsCompleted] || '';

    return (
        <div className="typing-phrase word-by-word" aria-label="Mot courant à taper">
            <div className="previous-words" aria-hidden={previousWords.length === 0}>
                {previousWords.map((p, i) => (
                    <span key={i} className={"prev-word " + (p.type === 'rainbow' ? 'word-rainbow' : p.type === 'alert' ? 'word-alert' : '')}>{p.clean}</span>
                ))}
            </div>
            <div className={"current-word " + (currentWordMeta?.type === 'rainbow' ? 'word-rainbow' : currentWordMeta?.type === 'alert' ? 'word-alert' : '')} aria-live="polite">
                {currentWordMeta?.clean.split('').map((char, idx) => {
                    const state = idx < typedSegment.length
                        ? (typedSegment[idx] === char ? 'correct' : 'incorrect')
                        : '';
                    return (
                        <span key={idx} className={state}>{char}</span>
                    );
                })}
            </div>
            <div className="next-word" aria-hidden={true}>
                {parsed[wordsCompleted + 1] && <span className={"hint " + (parsed[wordsCompleted + 1].type === 'rainbow' ? 'word-rainbow' : parsed[wordsCompleted + 1].type === 'alert' ? 'word-alert' : '')}>{parsed[wordsCompleted + 1].clean}</span>}
            </div>
        </div>
    );
};

interface TypingInputProps {
    value: string;
    onChange: (v: string) => void;
    disabled?: boolean;
    visuallyHidden?: boolean;
}

export const TypingInput: React.FC<TypingInputProps> = ({ value, onChange, disabled, visuallyHidden }) => {
    return (
        <div className={"typing-input-card" + (visuallyHidden ? " sr-only" : "")} onKeyDown={(e) => {
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