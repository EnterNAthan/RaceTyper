import React, { useState, useEffect, useCallback, useRef } from 'react';
import TypingPhrase, { TypingInput } from './components/TypingDisplay';
import ProgressBar from './components/ProgressBar';
import GameStats from './components/GameStats';
import MalusOverlay from './components/MalusOverlay';
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
    useWordFeedback();
    const { isFullscreen, enterFullscreen } = useKioskMode();

    const [roundResults, setRoundResults] = useState<PlayerData[]>([]);
    const [finalResults, setFinalResults] = useState<PlayerData[]>([]);

    // Lobby name editing
    const [editName, setEditName] = useState<string>(() => {
        const params = new URLSearchParams(window.location.search);
        return params.get('client') || localStorage.getItem('racetyper_client_id') || '';
    });

    // Malus state
    const [inputDisabled, setInputDisabled] = useState(false);
    const [sirenActive, setSirenActive] = useState(false);
    const [sleepActive, setSleepActive] = useState(false);
    const [showIntrusiveGif, setShowIntrusiveGif] = useState(false);
    const [keyboardDisabled, setKeyboardDisabled] = useState(false);

    // Malus effect handler
    const handleMalusEffect = useCallback((action: string) => {
        switch (action) {
            case 'SCREEN_SHAKE':
                document.body.classList.add('shake');
                setTimeout(() => document.body.classList.remove('shake'), 500);
                break;
            case 'SLEEP':
                setInputDisabled(true);
                setSleepActive(true);
                setTimeout(() => {
                    setInputDisabled(false);
                    setSleepActive(false);
                }, 3000);
                break;
            case 'TRIGGER_SIREN':
                setSirenActive(true);
                playSirenSound();
                setTimeout(() => setSirenActive(false), 2000);
                break;
            case 'SWAPKEY':
                // MVP: not implemented
                break;
            // ── Malus envoyés directement par le serveur via WebSocket ──
            case 'intrusive_gif':
                setShowIntrusiveGif(true);
                setTimeout(() => setShowIntrusiveGif(false), 3000);
                break;
            case 'disable_keyboard':
                setKeyboardDisabled(true);
                setInputDisabled(true);
                setTimeout(() => {
                    setKeyboardDisabled(false);
                    setInputDisabled(false);
                }, 1000);
                break;
        }
    }, []);

    // Game state management
    const [gameState, setGameState] = useState<GameState>('MENU');

    // Ref to bridge startGame from useTypingGame into useServerConnection callbacks
    const startGameRef = useRef<(phrase?: string) => void>(() => {});

    // Server connection (called first to provide sendPhraseComplete)
    const {
        connected,
        clientId,
        currentPhrase,
        gameStatus,
        players,
        currentRound,
        botActive,
        botDifficulty,
        botProgress,
        sendPhraseComplete,
        connect,
        disconnect,
    } = useServerConnection({
        onPhraseReceived: (phrase) => {
            console.log('New phrase received:', phrase);
            setRoundResults([]); // clear previous round results
            startGameRef.current(phrase); // use ref to avoid circular dependency
            setGameState('PLAYING'); // force game screen
        },
        onGameStatusChange: (status) => {
            console.log('Game status changed:', status);
            if (status === 'waiting') {
                setRoundResults([]);
                setFinalResults([]);
            }
        },
        onRoundResults: (results) => {
            console.log('Round results:', results);
            setRoundResults(results);
        },
        onGameOver: (results) => {
            console.log('Game over:', results);
            setFinalResults(results);
        },
        onMalusBonus: (event) => {
            console.log('Malus event:', event);
            handleMalusEffect(event.value);
        },
    });

    const handleNameConfirm = useCallback(() => {
        const name = editName.trim();
        if (!name) return;
        localStorage.setItem('racetyper_client_id', name);
        const params = new URLSearchParams(window.location.search);
        params.set('client', name);
        history.replaceState(null, '', `?${params.toString()}`);
        disconnect();
        connect();
    }, [editName, connect, disconnect]);

    // Typing game logic
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
            console.log('Phrase completed, sending to server...', stats);
            sendPhraseComplete(stats.timeTaken, stats.errorsCount, stats.bonus, stats.malus);
        },
    });

    // Keep ref in sync with latest startGame
    startGameRef.current = startGame;

    // Multiplayer flag
    const isMultiplayer = connected;

    // AI opponent settings (solo mode)
    const [aiEnabled, setAiEnabled] = useState(false);
    const [aiDifficulty, setAiDifficulty] = useState<AIDifficulty>('intermediate');

    // Countdown state
    const [countdown, setCountdown] = useState<number | null>(null);

    // Map difficulté serveur -> difficulté IA locale
    const mapServerDifficultyToAI = useCallback((d?: string): AIDifficulty => {
        switch ((d || '').toLowerCase()) {
            case 'debutant':
                return 'beginner';
            case 'moyen':
                return 'intermediate';
            case 'difficile':
                return 'expert';
            case 'impossible':
                return 'impossible';
            default:
                return 'intermediate';
        }
    }, []);

    const derivedAiEnabled = isMultiplayer ? botActive : aiEnabled;
    const derivedAiDifficulty: AIDifficulty = isMultiplayer
        ? mapServerDifficultyToAI(botDifficulty)
        : aiDifficulty;

    const { aiInput, aiProgress, aiErrors, aiCompleted, difficultySettings, aiWPM } = useAIOpponent({
        targetPhrase,
        isGameActive,
        isCompleted,
        // En multijoueur, le bot est géré côté serveur : désactiver le hook local
        aiEnabled: !isMultiplayer && derivedAiEnabled,
        difficulty: derivedAiDifficulty
    });

    // En multijoueur, on utilise les données de progression diffusées par le serveur.
    // En solo, on utilise le hook useAIOpponent local.
    const displayAiProgress = isMultiplayer ? (botProgress?.progress ?? 0) : aiProgress;
    const displayAiInput    = isMultiplayer ? (botProgress?.currentText ?? '') : aiInput;
    const displayAiErrors   = isMultiplayer ? (botProgress?.errors ?? 0) : aiErrors;
    const displayAiWPM      = isMultiplayer ? (botProgress?.wpm ?? 0) : aiWPM;

    // Check for game completion (win) - only in solo mode
    useEffect(() => {
        if (isCompleted && gameState === 'PLAYING' && !isMultiplayer) {
            setGameState('WIN');
        }
    }, [isCompleted, gameState, isMultiplayer]);

    // Check if AI completed before player (game over) - only in solo mode
    useEffect(() => {
        if (aiCompleted && aiEnabled && gameState === 'PLAYING' && !isCompleted && !isMultiplayer) {
            setGameState('GAMEOVER');
        }
    }, [aiCompleted, aiEnabled, isCompleted, gameState, isMultiplayer]);

    // Countdown effect (solo mode only)
    useEffect(() => {
        if (gameState === 'COUNTDOWN' && countdown !== null) {
            if (countdown > 0) {
                const timer = setTimeout(() => {
                    setCountdown(countdown - 1);
                }, 1000);
                return () => clearTimeout(timer);
            } else {
                setCountdown(null);
                setGameState('PLAYING');
                startGame();
            }
        }
    }, [countdown, gameState, startGame]);

    const handleStartFromMenu = async () => {
        setGameState('COUNTDOWN');
        setCountdown(3);
    };

    const handleReturnToMenu = () => {
        setGameState('MENU');
    };

    // Capture keyboard input globally only when playing
    useGlobalTyping({
        isGameActive: gameState === 'PLAYING' && isGameActive && !inputDisabled,
        isCompleted,
        userInput,
        targetPhrase,
        wordsCompleted,
        handleInputChange
    });

    return (
        <div className="app dark">
            {/* LOBBY SCREEN - multiplayer waiting for admin */}
            {isMultiplayer && gameState !== 'PLAYING' && gameStatus === 'waiting' && (
                <div className="menu-screen">
                    <div className="menu-container">
                        <h1 className="menu-title">RaceTyper</h1>
                        <p className="menu-subtitle">Course de frappe cooperative</p>
                        <div className="lobby-info">
                            <div className="lobby-name-edit">
                                <label className="menu-label" style={{ justifyContent: 'center', marginBottom: '8px' }}>
                                    Votre nom
                                </label>
                                <div className="lobby-name-row">
                                    <input
                                        className="typing-input"
                                        type="text"
                                        value={editName}
                                        onChange={(e) => setEditName(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter') handleNameConfirm(); }}
                                        maxLength={20}
                                        placeholder="Votre nom..."
                                    />
                                    <button className="btn primary" onClick={handleNameConfirm}>
                                        Confirmer
                                    </button>
                                </div>
                                {clientId && (
                                    <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '6px' }}>
                                        Connecté en tant que : <strong>{clientId}</strong>
                                    </p>
                                )}
                            </div>
                            <p style={{ color: 'var(--text-muted)', marginTop: '16px' }}>
                                En attente que l'arbitre d&eacute;marre la partie...
                            </p>
                            <div className="loader"></div>
                            {players.length > 0 && (
                                <div className="lobby-players">
                                    <h3>Joueurs connect&eacute;s ({players.length})</h3>
                                    {players.map(p => (
                                        <div
                                            key={p.client_id}
                                            className={`lobby-player ${p.client_id === clientId ? 'self' : ''}`}
                                        >
                                            {p.client_id}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* MENU SCREEN - solo mode only */}
            {!isMultiplayer && gameState === 'MENU' && (
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

            {/* COUNTDOWN SCREEN (solo mode) */}
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
                        {(gameStatus === 'playing' || !isMultiplayer) && (
                            <div className="top-progress">
                                <ProgressBar progress={progress} />
                            </div>
                        )}
                        <div style={{ marginTop: '10px', fontSize: '0.9em', opacity: 0.8 }}>
                            {isMultiplayer ? (
                                <>
                                    <span>{connected ? 'Connect\u00e9' : 'D\u00e9connect\u00e9'}</span>
                                    <span style={{ marginLeft: '15px' }}>{clientId}</span>
                                    <span style={{ marginLeft: '15px' }}>Round {currentRound + 1}/5</span>
                                </>
                            ) : (
                                <span>Mode solo</span>
                            )}
                        </div>
                        {!isMultiplayer && (
                            <>
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
                                    title={aiEnabled ? 'D\u00e9sactiver IA' : 'Activer IA'}
                                >
                                    {aiEnabled ? 'IA: ON' : 'IA: OFF'}
                                </button>
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
                                        title="Niveau de difficult\u00e9 de l'IA"
                                    >
                                        {Object.entries(DIFFICULTY_SETTINGS).map(([key, settings]) => (
                                            <option key={key} value={key}>
                                                {settings.name}
                                            </option>
                                        ))}
                                    </select>
                                )}
                            </>
                        )}
                        {!isFullscreen && (
                            <button
                                className="btn primary"
                                onClick={enterFullscreen}
                                title="Activer le mode kiosque"
                            >
                                Plein &eacute;cran
                            </button>
                        )}
                    </header>
                    <main className="app-main">
                        {/* Malus overlays */}
                        {sirenActive && (
                            <div className="siren-overlay" aria-live="assertive">
                                <span>SIREN!</span>
                            </div>
                        )}
                        {sleepActive && (
                            <div className="sleep-overlay" aria-live="polite">
                                <div className="sleep-box">
                                    <span>SLEEP - 3s</span>
                                </div>
                            </div>
                        )}

                        {/* MQTT malus overlays (GIF + keyboard disable) */}
                        <MalusOverlay
                            showGif={showIntrusiveGif}
                            keyboardDisabled={keyboardDisabled}
                        />

                        {/* Game paused by admin */}
                        {gameStatus === 'paused' && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>Pause</h2>
                                    <p>L'arbitre a mis le jeu en pause</p>
                                    <div className="loader"></div>
                                </div>
                            </div>
                        )}

                        {/* Round completed - waiting for others (multiplayer) */}
                        {isMultiplayer && gameStatus === 'round_wait' && roundResults.length === 0 && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>Round termin&eacute; !</h2>
                                    <p>Temps: {timeTaken.toFixed(2)}s &bull; Pr&eacute;cision: {accuracy}%</p>
                                    <p>En attente des autres joueurs...</p>
                                    <div className="loader"></div>
                                </div>
                            </div>
                        )}

                        {/* Round results */}
                        {roundResults.length > 0 && gameStatus !== 'game_over' && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>Classement Round {currentRound + 1}</h2>
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
                                                <span>{index === 0 ? '\ud83e\udd47' : index === 1 ? '\ud83e\udd48' : index === 2 ? '\ud83e\udd49' : `#${index + 1}`}</span>
                                                <span style={{ marginLeft: '10px' }}>{player.client_id}</span>
                                                <span style={{ marginLeft: 'auto', float: 'right' }}>+{player.score} pts</span>
                                            </div>
                                        ))}
                                    </div>
                                    <p style={{ marginTop: '16px', color: 'var(--text-muted)', fontSize: '14px' }}>
                                        Round suivant dans quelques secondes...
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Game over - final results */}
                        {gameStatus === 'game_over' && finalResults.length > 0 && (
                            <div className="win-overlay" aria-live="polite">
                                <div className="win-box">
                                    <h2>Partie termin&eacute;e !</h2>
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
                                                <span>{index === 0 ? '\ud83e\udd47' : index === 1 ? '\ud83e\udd48' : index === 2 ? '\ud83e\udd49' : `#${index + 1}`}</span>
                                                <span style={{ marginLeft: '15px' }}>{player.client_id}</span>
                                                <span style={{ marginLeft: 'auto', float: 'right', fontWeight: 'bold' }}>{player.score} pts</span>
                                            </div>
                                        ))}
                                    </div>
                                    {!isMultiplayer && (
                                        <button className="btn primary" onClick={handleReturnToMenu} style={{ marginTop: '20px' }}>
                                            Retour au menu
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Multiplayer scoreboard */}
                        {isMultiplayer && players.length > 0 && gameStatus === 'playing' && (
                            <section className="scoreboard-card">
                                <h3>Joueurs</h3>
                                {players
                                    .sort((a, b) => b.score - a.score)
                                    .map((player, index) => (
                                        <div
                                            key={player.client_id}
                                            className={`scoreboard-entry ${player.client_id === clientId ? 'self' : ''}`}
                                        >
                                            <span className="scoreboard-rank">#{index + 1}</span>
                                            <span className="scoreboard-name">{player.client_id}</span>
                                            <span className="scoreboard-score">{player.score} pts</span>
                                        </div>
                                    ))
                                }
                            </section>
                        )}

                        <section className="typing-card">
                            <TypingPhrase targetPhrase={targetPhrase} userInput={userInput} wordsCompleted={wordsCompleted} isCompleted={isCompleted} />
                        </section>

                        {/* AI opponent display (solo mode only) */}
                        {((!isMultiplayer && aiEnabled) || (isMultiplayer && botActive)) && (
                            <section className="typing-card ai-opponent" aria-label="AI opponent">
                                <div className="ai-header">
                                    <div className="ai-title">
                                        <span className="ai-label">{isMultiplayer ? 'BOT-IA' : 'Opponent'}</span>
                                        <span className="ai-difficulty">
                                            {isMultiplayer && botDifficulty
                                                ? botDifficulty
                                                : difficultySettings.name}
                                        </span>
                                    </div>
                                    <div className="ai-metrics">
                                        <div className="metric">
                                            <span className="metric-label">Progress</span>
                                            <span className="metric-value">{displayAiProgress.toFixed(1)}%</span>
                                        </div>
                                        <div className="metric">
                                            <span className="metric-label">WPM</span>
                                            <span className="metric-value">{displayAiWPM}</span>
                                        </div>
                                        <div className="metric">
                                            <span className="metric-label">Chars</span>
                                            <span className="metric-value">{displayAiInput.length}</span>
                                        </div>
                                        <div className="metric">
                                            <span className="metric-label">Errors</span>
                                            <span className={`metric-value ${displayAiErrors > 0 ? 'error' : ''}`}>{displayAiErrors}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="ai-typing">
                                    <div className="ai-line">
                                        {displayAiInput || <span className="ai-placeholder">Waiting for opponent...</span>}
                                    </div>
                                    <div className="ai-progress">
                                        <ProgressBar progress={displayAiProgress} />
                                    </div>
                                </div>
                            </section>
                        )}

                        <section className="input-wrapper">
                            <TypingInput
                                value={userInput}
                                onChange={handleInputChange}
                                disabled={isCompleted || inputDisabled}
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

            {/* WIN SCREEN (solo mode only) */}
            {!isMultiplayer && gameState === 'WIN' && (
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

            {/* GAME OVER SCREEN (solo mode - AI won) */}
            {!isMultiplayer && gameState === 'GAMEOVER' && (
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

let sirenAudioCtx: AudioContext | null = null;
function playSirenSound() {
    try {
        if (!sirenAudioCtx || sirenAudioCtx.state === 'closed') {
            sirenAudioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        }
        if (sirenAudioCtx.state === 'suspended') {
            sirenAudioCtx.resume();
        }
        const ctx = sirenAudioCtx;
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = 'sawtooth';
        o.frequency.value = 600;
        g.gain.value = 0.1;
        o.connect(g);
        g.connect(ctx.destination);
        const now = ctx.currentTime;
        o.start(now);
        o.frequency.setValueAtTime(600, now);
        o.frequency.linearRampToValueAtTime(1200, now + 0.5);
        o.frequency.linearRampToValueAtTime(600, now + 1.0);
        o.frequency.linearRampToValueAtTime(1200, now + 1.5);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 2.0);
        o.stop(now + 2.0);
    } catch {
        // AudioContext not available
    }
}

export default App;
