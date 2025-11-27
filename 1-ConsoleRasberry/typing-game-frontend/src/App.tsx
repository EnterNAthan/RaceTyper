import React from 'react';
import TypingPhrase, { TypingInput } from './components/TypingDisplay';
import ProgressBar from './components/ProgressBar';
import GameStats from './components/GameStats';
import { useTypingGame } from './hooks/useTypingGame';
import { useArcadeEffects } from './hooks/useArcadeEffects';
import { useWordFeedback } from './hooks/useWordFeedback';
import { useGlobalTyping } from './hooks/useGlobalTyping';
import { useKioskMode } from './hooks/useKioskMode';
import { useState } from 'react';
import useAIOpponent, { DIFFICULTY_SETTINGS, AIDifficulty } from './hooks/useAIOpponent';

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

    // AI opponent toggle
    const [aiEnabled, setAiEnabled] = useState(false);
    const [aiDifficulty, setAiDifficulty] = useState<AIDifficulty>('intermediate');
    const { aiInput, aiProgress, aiErrors, difficultySettings, aiWPM } = useAIOpponent({ 
        targetPhrase, 
        isGameActive, 
        isCompleted, 
        aiEnabled, 
        difficulty: aiDifficulty 
    });

    // Capture keyboard input globally so user doesn't need to focus the field
    useGlobalTyping({ isGameActive, isCompleted, userInput, targetPhrase, wordsCompleted, handleInputChange });

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
                        <button
                            className={"btn secondary"}
                            onClick={() => setAiEnabled(v => !v)}
                            title={aiEnabled ? 'Désactiver IA' : 'Activer IA'}
                        >
                            {aiEnabled ? 'IA: ON' : 'IA: OFF'}
                        </button>
                        
                        {/* AI Difficulty Selector */}
                        {aiEnabled && (
                            <select 
                                value={aiDifficulty} 
                                onChange={(e) => setAiDifficulty(e.target.value as AIDifficulty)}
                                style={{
                                    padding: '8px 12px',
                                    borderRadius: '4px',
                                    border: '1px solid #ccc',
                                    backgroundColor: '#fff',
                                    fontSize: '14px',
                                    cursor: 'pointer'
                                }}
                                title="Niveau de difficulté de l'IA"
                            >
                                {Object.entries(DIFFICULTY_SETTINGS).map(([key, settings]) => (
                                    <option key={key} value={key}>
                                        {settings.emoji} {settings.name}
                                    </option>
                                ))}
                            </select>
                        )}
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
                        {!isCompleted && (
                            <>
                                <section className="typing-card">
                                    <TypingPhrase targetPhrase={targetPhrase} userInput={userInput} wordsCompleted={wordsCompleted} isCompleted={isCompleted} />
                                </section>

                                {/* AI opponent display */}
                                {aiEnabled && (
                                    <section className="typing-card ai-opponent" aria-label="AI opponent">
                                        <div className="ai-header">
                                            {difficultySettings.emoji} Adversaire IA - {difficultySettings.name}
                                            <div className="ai-stats" style={{fontSize: '12px', marginTop: '4px'}}>
                                                <span>Progress: {aiProgress.toFixed(1)}%</span>
                                                <span>WPM: {aiWPM}</span>
                                                <span>Chars: {aiInput.length}</span>
                                                <span style={{color: aiErrors > 0 ? '#ff6b6b' : '#666'}}>
                                                    Erreurs: {aiErrors}
                                                </span>
                                            </div>
                                            <div style={{fontSize: '11px', color: '#888', fontStyle: 'italic'}}>
                                                {difficultySettings.description}
                                            </div>
                                        </div>
                                        <div className="ai-typing">
                                            <div className="ai-line" style={{
                                                fontFamily: 'monospace',
                                                fontSize: '1.1em',
                                                padding: '8px',
                                                backgroundColor: 'rgba(0,100,255,0.1)',
                                                border: '1px solid rgba(0,100,255,0.3)',
                                                borderRadius: '4px',
                                                minHeight: '2em',
                                                wordBreak: 'break-all',
                                                transition: 'background-color 0.3s ease'
                                            }}>
                                                {aiInput || <span style={{color: '#666'}}>IA en attente...</span>}
                                            </div>
                                            <div className="ai-progress" style={{marginTop: '8px'}}>
                                                <ProgressBar progress={aiProgress} />
                                            </div>
                                        </div>
                                    </section>
                                )}
                            </>
                        )}
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