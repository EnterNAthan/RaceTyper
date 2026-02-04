import React, { useState } from 'react';
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
import { useServerConnection, PlayerData } from './hooks/useServerConnection';

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
    } = useTypingGame({
        targetPhrase: currentPhrase,
        onPhraseComplete: (stats) => {
            console.log('✅ Phrase completed, sending to server...', stats);
            sendPhraseComplete(stats.timeTaken, stats.errorsCount, stats.bonus, stats.malus);
        },
    });

    // Capture keyboard input globally so user doesn't need to focus the field
    useGlobalTyping({ isGameActive, isCompleted, userInput, targetPhrase, wordsCompleted, handleInputChange });

    return (
                <div className="app dark">
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
                                        {settings.emoji} {settings.name}
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
                                <span>GOOD!</span>
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
                </div>
    );
};

export default App;