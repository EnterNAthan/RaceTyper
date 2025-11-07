import React from 'react';
import TypingPhrase, { TypingInput } from './components/TypingDisplay';
import ProgressBar from './components/ProgressBar';
import GameStats from './components/GameStats';
import { useTypingGame } from './hooks/useTypingGame';
import { useArcadeEffects } from './hooks/useArcadeEffects';
import { useWordFeedback } from './hooks/useWordFeedback';
import { useGlobalTyping } from './hooks/useGlobalTyping';
import { useKioskMode } from './hooks/useKioskMode';

const App: React.FC = () => {
    useArcadeEffects();
    const { showGood, showBad, count } = useWordFeedback();
    const { isFullscreen, enterFullscreen } = useKioskMode();
    const {
        targetPhrase,
        userInput,
        progress,
        attempts,
        accuracy,
        timeTaken,
        handleInputChange,
        startGame,
        isGameActive,
        isCompleted,
        wordsCompleted,
    } = useTypingGame();

    // Capture keyboard input globally so user doesn't need to focus the field
    useGlobalTyping({ isGameActive, isCompleted, userInput, handleInputChange });

    return (
                <div className="app dark">
                    <header className="app-header with-progress">
                        <h1>RaceTyper</h1>
                        <div className="top-progress">
                            <ProgressBar progress={progress} />
                        </div>
                        <button
                            className="btn primary"
                            onClick={async () => { await enterFullscreen(); startGame(); }}
                            title={isFullscreen ? 'Fullscreen actif' : 'Activer le mode kiosque'}
                        >
                            {isGameActive ? 'Restart' : 'Start'}
                        </button>
                    </header>
                    <main className="app-main">
                        {showGood && (
                            <div className="good-overlay" aria-live="polite">
                                <span>GOOD!</span>
                            </div>
                        )}
                        {showBad && (
                            <div className="bad-overlay" aria-live="polite">
                                <span>ERREUR&nbsp;!</span>
                            </div>
                        )}
                        {isCompleted && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>VICTOIRE !</h2>
                                    <p>Temps: {timeTaken.toFixed(2)}s • Précision: {accuracy}%</p>
                                    <button className="btn primary" onClick={startGame}>Rejouer</button>
                                </div>
                            </div>
                        )}
                        <section className="typing-card">
                            <TypingPhrase targetPhrase={targetPhrase} userInput={userInput} wordsCompleted={wordsCompleted} isCompleted={isCompleted} />
                        </section>
                        <section className="input-wrapper">
                            <TypingInput 
                                value={userInput} 
                                onChange={handleInputChange} 
                                disabled={isCompleted || !isGameActive} 
                                visuallyHidden={isGameActive} 
                            />
                        </section>
                        <section className="stats-card">
                            <GameStats 
                                attempts={attempts} 
                                accuracy={accuracy} 
                                timeTaken={timeTaken} 
                            />
                        </section>
                    </main>
                </div>
    );
};

export default App;