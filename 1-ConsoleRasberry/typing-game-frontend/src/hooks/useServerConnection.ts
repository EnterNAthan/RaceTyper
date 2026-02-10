import { useState, useEffect, useCallback, useRef } from 'react';

export interface ServerMessage {
    type: string;
    [key: string]: any;
}

export interface PlayerData {
    client_id: string;
    score: number;
    rank?: number;
}

export interface ServerConnectionState {
    connected: boolean;
    clientId: string;
    currentPhrase: string;
    gameStatus: 'waiting' | 'playing' | 'round_wait' | 'game_over' | 'paused';
    players: PlayerData[];
    currentRound: number;
    totalRounds: number;
}

interface UseServerConnectionProps {
    serverUrl?: string;
    onPhraseReceived?: (phrase: string) => void;
    onGameStatusChange?: (status: string) => void;
    onRoundResults?: (results: PlayerData[]) => void;
    onGameOver?: (finalResults: PlayerData[]) => void;
    onMalusBonus?: (event: { type: string; value: string }) => void;
}

// Resolve server URL: ?server=IP:PORT in URL takes priority, then prop, then default
const getServerUrl = (propUrl?: string): string => {
    const params = new URLSearchParams(window.location.search);
    const urlServer = params.get('server');
    if (urlServer) {
        // Accept "192.168.1.10:8080" or "ws://192.168.1.10:8080"
        return urlServer.startsWith('ws') ? urlServer : `ws://${urlServer}`;
    }
    return propUrl || `ws://${window.location.hostname}:8080`;
};

export const useServerConnection = ({
    serverUrl,
    onPhraseReceived,
    onGameStatusChange,
    onRoundResults,
    onGameOver,
    onMalusBonus,
}: UseServerConnectionProps = {}) => {
    const resolvedServerUrl = getServerUrl(serverUrl);
    const [state, setState] = useState<ServerConnectionState>({
        connected: false,
        clientId: '',
        currentPhrase: '',
        gameStatus: 'waiting',
        players: [],
        currentRound: 0,
        totalRounds: 5,
    });

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttempts = useRef(0);

    // Store callbacks in refs to avoid recreating handleMessage/connect on every render
    const callbacksRef = useRef({ onPhraseReceived, onGameStatusChange, onRoundResults, onGameOver, onMalusBonus });
    callbacksRef.current = { onPhraseReceived, onGameStatusChange, onRoundResults, onGameOver, onMalusBonus };

    // Get or create client ID
    const getClientId = useCallback(() => {
        const params = new URLSearchParams(window.location.search);
        const urlClientId = params.get('client');

        if (urlClientId) {
            localStorage.setItem('racetyper_client_id', urlClientId);
            return urlClientId;
        }

        let storedId = localStorage.getItem('racetyper_client_id');
        if (!storedId) {
            storedId = `player-${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('racetyper_client_id', storedId);
        }

        return storedId;
    }, []);

    // Handle incoming messages from server
    // No callback dependencies — reads from callbacksRef to stay stable
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message: ServerMessage = JSON.parse(event.data);
            console.log('📥 Server message:', message);
            const cbs = callbacksRef.current;

            switch (message.type) {
                case 'connection_accepted':
                    console.log('✅ Connection accepted');
                    setState(prev => ({
                        ...prev,
                        connected: true,
                        clientId: message.client_id || prev.clientId,
                    }));
                    break;

                case 'new_phrase':
                    console.log('📝 New phrase:', message.phrase);
                    setState(prev => ({
                        ...prev,
                        currentPhrase: message.phrase,
                        gameStatus: 'playing',
                        currentRound: message.round_number ?? prev.currentRound,
                    }));
                    cbs.onPhraseReceived?.(message.phrase);
                    cbs.onGameStatusChange?.('playing');
                    break;

                case 'player_update':
                    console.log('👥 Player update:', message.scores);
                    if (message.scores) {
                        const playerArray = Object.entries(message.scores).map(([id, score]) => ({
                            client_id: id,
                            score: score as number,
                        }));
                        setState(prev => ({ ...prev, players: playerArray }));
                    }
                    break;

                case 'round_wait':
                    console.log('⏳ Round wait');
                    setState(prev => ({ ...prev, gameStatus: 'round_wait' }));
                    cbs.onGameStatusChange?.('round_wait');
                    break;

                case 'round_classement':
                    console.log('🏆 Round results:', message.classement);
                    if (message.classement) {
                        const results = message.classement.map((player: any) => ({
                            client_id: player.client_id,
                            score: player.score_added,
                            rank: player.rank,
                        }));
                        // Utiliser global_scores pour le scoreboard global
                        const globalPlayers = message.global_scores
                            ? Object.entries(message.global_scores).map(([id, score]) => ({
                                client_id: id,
                                score: score as number,
                            }))
                            : results;
                        setState(prev => ({ ...prev, players: globalPlayers, gameStatus: 'round_wait' }));
                        cbs.onRoundResults?.(results);
                    }
                    break;

                case 'game_over':
                    console.log('🎮 Game over:', message.final_scores);
                    setState(prev => ({ ...prev, gameStatus: 'game_over' }));
                    if (message.final_scores) {
                        const sorted = Object.entries(message.final_scores)
                            .sort(([, a], [, b]) => (b as number) - (a as number));
                        const finalResults = sorted.map(([id, score], index) => ({
                            client_id: id,
                            score: score as number,
                            rank: index + 1,
                        }));
                        cbs.onGameOver?.(finalResults);
                    }
                    cbs.onGameStatusChange?.('game_over');
                    break;

                case 'hardware_action':
                    console.log('⚡ Hardware action:', message.action);
                    cbs.onMalusBonus?.({ type: 'malus', value: message.action });
                    break;

                case 'kicked':
                    console.log('❌ Kicked from game:', message.message);
                    setState(prev => ({ ...prev, connected: false }));
                    break;

                case 'game_paused':
                    console.log('⏸️ Game paused');
                    setState(prev => ({ ...prev, gameStatus: 'paused' }));
                    cbs.onGameStatusChange?.('paused');
                    break;

                case 'game_reset':
                    console.log('🔄 Game reset');
                    setState(prev => ({
                        ...prev,
                        gameStatus: 'waiting',
                        currentRound: 0,
                        currentPhrase: '',
                        players: prev.players.map(p => ({ ...p, score: 0 })),
                    }));
                    cbs.onGameStatusChange?.('waiting');
                    break;

                case 'game_status':
                    console.log('📊 Game status:', message.status);
                    setState(prev => ({ ...prev, gameStatus: message.status }));
                    cbs.onGameStatusChange?.(message.status);
                    break;

                case 'admin_message':
                    console.log('📢 Admin message:', message.message);
                    break;

                case 'error':
                    console.error('❌ Server error:', message.message);
                    break;

                default:
                    console.log('❓ Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error parsing server message:', error);
        }
    }, []);

    // Connect to WebSocket server
    const connect = useCallback(() => {
        const clientId = getClientId();
        const wsUrl = `${resolvedServerUrl}/ws/${clientId}`;

        console.log('🔌 Connecting to:', wsUrl);

        try {
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                reconnectAttempts.current = 0;
                setState(prev => ({
                    ...prev,
                    connected: true,
                    clientId,
                }));
            };

            ws.onmessage = handleMessage;

            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                setState(prev => ({ ...prev, connected: false }));

                // Attempt to reconnect with exponential backoff
                if (reconnectAttempts.current < 10) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
                    console.log(`⏳ Reconnecting in ${delay}ms...`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        reconnectAttempts.current++;
                        connect();
                    }, delay);
                }
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('Error creating WebSocket:', error);
        }
    }, [resolvedServerUrl, getClientId, handleMessage]);

    // Disconnect from server
    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    }, []);

    // Send message to server
    const sendMessage = useCallback((message: ServerMessage) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            console.log('📤 Sending message:', message);
            wsRef.current.send(JSON.stringify(message));
        } else {
            console.warn('⚠️ WebSocket not connected, cannot send message');
        }
    }, []);

    // Send phrase completion
    const sendPhraseComplete = useCallback((timeTaken: number, errorsCount: number, bonus: any[], malus: any[]) => {
        const objects_triggered = [
            ...bonus.map((word: string) => ({ type: 'bonus', word, success: true })),
            ...malus.map((word: string) => ({ type: 'malus', word, success: true })),
        ];
        sendMessage({
            type: 'phrase_finished',
            action: 'phrase_finished',
            time_taken: timeTaken,
            errors: errorsCount,
            objects_triggered,
        });
    }, [sendMessage]);

    // Send validation result
    const sendValidation = useCallback((isValid: boolean, currentInput: string) => {
        sendMessage({
            type: 'validation_result',
            valid: isValid,
            current_input: currentInput,
        });
    }, [sendMessage]);

    // Connect on mount
    useEffect(() => {
        connect();

        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    return {
        ...state,
        connect,
        disconnect,
        sendMessage,
        sendPhraseComplete,
        sendValidation,
    };
};
