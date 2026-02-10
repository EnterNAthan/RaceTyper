import React, { useState, useEffect } from 'react';
import TypingPhrase, { TypingInput } from './components/TypingDisplay';
import ProgressBar from './components/ProgressBar';
import GameStats from './components/GameStats';
import { useTypingGame } from './hooks/useTypingGame';
import { useArcadeEffects } from './hooks/useArcadeEffects';
import { useWordFeedback } from './hooks/useWordFeedback';
import { useGlobalTyping } from './hooks/useGlobalTyping';
import { useKioskMode } from './hooks/useKioskMode';
import useAIOpponent, { DIFFICULTY_SETTINGS, AIDifficulty } from './hooks/useAIOpponent';
import { useServerConnection, PlayerData } from './hooks/useServerConnection';

type GameState = 'MENU' | 'COUNTDOWN' | 'PLAYING' | 'WIN' | 'GAMEOVER';

const App: React.FC = () => {
    useArcadeEffects();
    const { showGood, showBad } = useWordFeedback();
    const { isFullscreen, enterFullscreen } = useKioskMode();

    const [roundResults, setRoundResults] = useState<PlayerData[]>([]);
    const [finalResults, setFinalResults] = useState<PlayerData[]>([]);

    // Server connection
    const {
        connected,
        clientId,
        currentPhrase,
        gameStatus,
        players,
        currentRound,
        sendPhraseComplete,
    } = useServerConnection({
        onPhraseReceived: (phrase) => {
            console.log('🎯 New phrase received, starting game...');
            startGame();
        },
        onRoundResults: (results) => {
            console.log('🏆 Round results:', results);
            setRoundResults(results);
        },
        onGameOver: (results) => {
            console.log('🎮 Game over:', results);
            setFinalResults(results);
        },
    });

    // Typing game logic (single hook instance wired to server currentPhrase)
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
    } = useTypingGame({
        targetPhrase: currentPhrase,
        onPhraseComplete: (stats) => {
            // send stats to server when local phrase completed
            console.log('✅ Phrase completed, sending to server...', stats);
            sendPhraseComplete(stats.timeTaken, stats.errorsCount, stats.bonus, stats.malus);
        },
    });

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
                        {gameStatus === 'playing' && (
                            <div className="top-progress">
                                <ProgressBar progress={progress} />
                            </div>
                        )}
                        <div style={{ marginTop: '10px', fontSize: '0.9em', opacity: 0.8 }}>
                            <span>🔌 {connected ? 'Connecté' : 'Déconnecté'}</span>
                            {connected && (
                                <>
                                    <span style={{ marginLeft: '15px' }}>👤 {clientId}</span>
                                    <span style={{ marginLeft: '15px' }}>🎯 Round {currentRound + 1}/5</span>
                                </>
                            )}
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
                                        {settings.name}
                                    </option>
                                ))}
                            </select>
                        )}
                        {!isFullscreen && (
                            <button
                                className="btn primary"
                                onClick={enterFullscreen}
                                title="Activer le mode kiosque"
                            >
                                Plein écran
                            </button>
                        )}
                    </header>
                    <main className="app-main">
                        {showGood && (
                            <div className="good-overlay" aria-live="polite">
                                <span>Correct</span>
                            </div>
                        )}
                        {showBad && (
                            <div className="bad-overlay" aria-live="polite">
                                <span>ERREUR&nbsp;!</span>
                            </div>
                        )}

                        {/* Waiting for game to start */}
                        {gameStatus === 'waiting' && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>En attente...</h2>
                                    <p>Connecté en tant que: <strong>{clientId}</strong></p>
                                    <p>En attente que l'arbitre démarre la partie</p>
                                    <div className="loader"></div>
                                </div>
                            </div>
                        )}

                        {/* Round completed - waiting for others */}
                        {gameStatus === 'round_wait' && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>Round terminé !</h2>
                                    <p>Temps: {timeTaken.toFixed(2)}s • Précision: {accuracy}%</p>
                                    <p>En attente des autres joueurs...</p>
                                    <div className="loader"></div>
                                </div>
                            </div>
                        )}

                        {/* Round results */}
                        {roundResults.length > 0 && gameStatus !== 'game_over' && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>🏆 Classement Round {currentRound}</h2>
                                    <div className="ranking-list">
                                        {roundResults.map((player, index) => (
                                            <div
                                                key={player.client_id}
                                                className={`rank-item ${player.client_id === clientId ? 'highlight' : ''}`}
                                                style={{
                                                    padding: '10px',
                                                    margin: '5px 0',
                                                    background: player.client_id === clientId ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                                                    borderRadius: '5px',
                                                }}
                                            >
                                                <span>{index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}</span>
                                                <span style={{ marginLeft: '10px' }}>{player.client_id}</span>
                                                <span style={{ marginLeft: 'auto', float: 'right' }}>{player.score} pts</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Game over - final results */}
                        {gameStatus === 'game_over' && finalResults.length > 0 && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>🎮 Partie terminée !</h2>
                                    <h3>Classement final</h3>
                                    <div className="ranking-list">
                                        {finalResults.map((player, index) => (
                                            <div
                                                key={player.client_id}
                                                className={`rank-item ${player.client_id === clientId ? 'highlight' : ''}`}
                                                style={{
                                                    padding: '15px',
                                                    margin: '10px 0',
                                                    background: player.client_id === clientId ? 'rgba(0, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)',
                                                    borderRadius: '8px',
                                                    fontSize: '1.2em',
                                                }}
                                            >
                                                <span>{index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}</span>
                                                <span style={{ marginLeft: '15px' }}>{player.client_id}</span>
                                                <span style={{ marginLeft: 'auto', float: 'right', fontWeight: 'bold' }}>{player.score} pts</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
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

                        {/* Playing state */}
                        {gameStatus === 'playing' && !isCompleted && (
                            <>
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
                            </>
                        )}
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