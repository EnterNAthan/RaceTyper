import React from 'react';
import TypingPhrase, { TypingInput } from './components/TypingDisplay';
import ProgressBar from './components/ProgressBar';
import GameStats from './components/GameStats';
import { useTypingGame } from './hooks/useTypingGame';
import { useArcadeEffects } from './hooks/useArcadeEffects';
import { useWordFeedback } from './hooks/useWordFeedback';
import { useGlobalTyping } from './hooks/useGlobalTyping';
import { useKioskMode } from './hooks/useKioskMode';
import { useState, useEffect } from 'react';
import useAIOpponent, { DIFFICULTY_SETTINGS, AIDifficulty } from './hooks/useAIOpponent';

type GameState = 'MENU' | 'COUNTDOWN' | 'PLAYING' | 'WIN' | 'GAMEOVER';

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

    // Game state management
    const [gameState, setGameState] = useState<GameState>('MENU');
    
    // AI opponent settings
    const [aiEnabled, setAiEnabled] = useState(false);
    const [aiDifficulty, setAiDifficulty] = useState<AIDifficulty>('intermediate');
    
    // Countdown state
    const [countdown, setCountdown] = useState<number | null>(null);
    
    const { aiInput, aiProgress, aiErrors, aiCompleted, difficultySettings, aiWPM } = useAIOpponent({ 
        targetPhrase, 
        isGameActive, 
        isCompleted, 
        aiEnabled, 
        difficulty: aiDifficulty 
    });

    // Check for game completion (win)
    useEffect(() => {
        if (isCompleted && gameState === 'PLAYING') {
            setGameState('WIN');
        }
    }, [isCompleted, gameState]);

    // Check if AI completed before player (game over)
    useEffect(() => {
        if (aiCompleted && aiEnabled && gameState === 'PLAYING' && !isCompleted) {
            setGameState('GAMEOVER');
        }
    }, [aiCompleted, aiEnabled, isCompleted, gameState]);

    // Countdown effect
    useEffect(() => {
        if (gameState === 'COUNTDOWN' && countdown !== null) {
            if (countdown > 0) {
                const timer = setTimeout(() => {
                    setCountdown(countdown - 1);
                }, 1000);
                return () => clearTimeout(timer);
            } else {
                // Countdown finished, start the game
                setCountdown(null);
                setGameState('PLAYING');
                startGame();
            }
        }
    }, [countdown, gameState, startGame]);

    const handleStartFromMenu = async () => {
        // Removed fullscreen/kiosk mode to allow mouse cursor
        setGameState('COUNTDOWN');
        setCountdown(3);
    };

    const handleReturnToMenu = () => {
        setGameState('MENU');
    };

    // Capture keyboard input globally only when playing
    useGlobalTyping({ 
        isGameActive: gameState === 'PLAYING' && isGameActive, 
        isCompleted, 
        userInput, 
        targetPhrase, 
        wordsCompleted, 
        handleInputChange 
    });

    return (
        <div className="app dark">
            {/* MENU SCREEN */}
            {gameState === 'MENU' && (
                <div className="menu-screen">
                    <div className="menu-container">
                        <h1 className="menu-title">RaceTyper</h1>
                        <p className="menu-subtitle">Test your typing speed</p>
                        
                        <div className="menu-options">
                            <div className="menu-option">
                                <label className="menu-label">
                                    <input
                                        type="checkbox"
                                        checked={aiEnabled}
                                        onChange={(e) => setAiEnabled(e.target.checked)}
                                        className="menu-checkbox"
                                    />
                                    <span>Enable AI Opponent</span>
                                </label>
                            </div>
                            
                            {aiEnabled && (
                                <div className="menu-option">
                                    <label className="menu-label">Difficulty</label>
                                    <select 
                                        className="menu-select"
                                        value={aiDifficulty} 
                                        onChange={(e) => setAiDifficulty(e.target.value as AIDifficulty)}
                                    >
                                        {Object.entries(DIFFICULTY_SETTINGS).map(([key, settings]) => (
                                            <option key={key} value={key}>
                                                {settings.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}
                        </div>
                        
                        <button className="btn primary menu-start-btn" onClick={handleStartFromMenu}>
                            Start Game
                        </button>
                    </div>
                </div>
            )}

            {/* COUNTDOWN SCREEN */}
            {gameState === 'COUNTDOWN' && countdown !== null && (
                <div className="countdown-overlay" aria-live="polite">
                    <div className="countdown-number">
                        {countdown === 0 ? 'GO!' : countdown}
                    </div>
                </div>
            )}

            {/* GAME SCREEN */}
            {gameState === 'PLAYING' && (
                <>
                    <header className="app-header with-progress">
                        <h1>RaceTyper</h1>
                        <div className="header-controls">
                            <button className="btn secondary" onClick={handleReturnToMenu}>
                                Quit
                            </button>
                        </div>
                        <div className="top-progress">
                            <ProgressBar progress={progress} />
                        </div>
                    </header>
                    <main className="app-main">
                        {showGood && (
                            <div className="good-overlay" aria-live="polite">
                                <span>Correct</span>
                            </div>
                        )}
                        {showBad && (
                            <div className="bad-overlay" aria-live="polite">
                                <span>Error</span>
                            </div>
                        )}
                        
                        <section className="typing-card">
                            <TypingPhrase targetPhrase={targetPhrase} userInput={userInput} wordsCompleted={wordsCompleted} isCompleted={isCompleted} />
                        </section>

                        {/* AI opponent display */}
                        {aiEnabled && (
                            <section className="typing-card ai-opponent" aria-label="AI opponent">
                                <div className="ai-header">
                                    <div className="ai-title">
                                        <span className="ai-label">Opponent</span>
                                        <span className="ai-difficulty">{difficultySettings.name}</span>
                                    </div>
                                    <div className="ai-metrics">
                                        <div className="metric">
                                            <span className="metric-label">Progress</span>
                                            <span className="metric-value">{aiProgress.toFixed(1)}%</span>
                                        </div>
                                        <div className="metric">
                                            <span className="metric-label">WPM</span>
                                            <span className="metric-value">{aiWPM}</span>
                                        </div>
                                        <div className="metric">
                                            <span className="metric-label">Chars</span>
                                            <span className="metric-value">{aiInput.length}</span>
                                        </div>
                                        <div className="metric">
                                            <span className="metric-label">Errors</span>
                                            <span className={`metric-value ${aiErrors > 0 ? 'error' : ''}`}>{aiErrors}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="ai-typing">
                                    <div className="ai-line">
                                        {aiInput || <span className="ai-placeholder">Waiting for opponent...</span>}
                                    </div>
                                    <div className="ai-progress">
                                        <ProgressBar progress={aiProgress} />
                                    </div>
                                </div>
                            </section>
                        )}
                        
                        <section className="input-wrapper">
                            <TypingInput 
                                value={userInput} 
                                onChange={handleInputChange} 
                                disabled={isCompleted} 
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
                </>
            )}

            {/* WIN SCREEN */}
            {gameState === 'WIN' && (
                <div className="win-overlay" aria-live="polite">
                    <div className="win-box">
                        <h2>Complete</h2>
                        <div className="win-stats">
                            <div className="win-stat">
                                <span className="win-stat-label">Time</span>
                                <span className="win-stat-value">{timeTaken.toFixed(2)}s</span>
                            </div>
                            <div className="win-stat">
                                <span className="win-stat-label">Accuracy</span>
                                <span className="win-stat-value">{accuracy}%</span>
                            </div>
                        </div>
                        <button className="btn primary" onClick={handleReturnToMenu}>Back to Menu</button>
                    </div>
                </div>
            )}
            
            {/* GAME OVER SCREEN */}
            {gameState === 'GAMEOVER' && (
                <div className="gameover-overlay" aria-live="polite">
                    <div className="gameover-box">
                        <h2>Game Over</h2>
                        <p className="gameover-message">The opponent finished first!</p>
                        <div className="gameover-stats">
                            <div className="gameover-stat">
                                <span className="gameover-stat-label">Your Progress</span>
                                <span className="gameover-stat-value">{progress.toFixed(1)}%</span>
                            </div>
                            <div className="gameover-stat">
                                <span className="gameover-stat-label">Opponent</span>
                                <span className="gameover-stat-value">100%</span>
                            </div>
                        </div>
                        <button className="btn primary" onClick={handleReturnToMenu}>Back to Menu</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default App;