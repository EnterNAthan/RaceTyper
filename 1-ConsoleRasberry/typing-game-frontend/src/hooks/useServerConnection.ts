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

export const useServerConnection = ({
    serverUrl = 'ws://127.0.0.1:8080',
    onPhraseReceived,
    onGameStatusChange,
    onRoundResults,
    onGameOver,
    onMalusBonus,
}: UseServerConnectionProps = {}) => {
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
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttempts = useRef(0);

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
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message: ServerMessage = JSON.parse(event.data);
            console.log('📥 Server message:', message);

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
                    onPhraseReceived?.(message.phrase);
                    onGameStatusChange?.('playing');
                    break;

                case 'player_update':
                    console.log('👥 Player update:', message.players);
                    if (message.players) {
                        const playerArray = Object.entries(message.players).map(([id, data]: [string, any]) => ({
                            client_id: id,
                            score: data.score || 0,
                        }));
                        setState(prev => ({ ...prev, players: playerArray }));
                    }
                    break;

                case 'round_wait':
                    console.log('⏳ Round wait');
                    setState(prev => ({ ...prev, gameStatus: 'round_wait' }));
                    onGameStatusChange?.('round_wait');
                    break;

                case 'round_classement':
                    console.log('🏆 Round results:', message.ranking);
                    if (message.ranking) {
                        const results = message.ranking.map((player: any, index: number) => ({
                            client_id: player.client_id,
                            score: player.score,
                            rank: index + 1,
                        }));
                        setState(prev => ({ ...prev, players: results }));
                        onRoundResults?.(results);
                    }
                    break;

                case 'game_over':
                    console.log('🎮 Game over:', message.final_ranking);
                    setState(prev => ({ ...prev, gameStatus: 'game_over' }));
                    if (message.final_ranking) {
                        const finalResults = message.final_ranking.map((player: any, index: number) => ({
                            client_id: player.client_id,
                            score: player.score,
                            rank: index + 1,
                        }));
                        onGameOver?.(finalResults);
                    }
                    onGameStatusChange?.('game_over');
                    break;

                case 'malus_bonus_event':
                    console.log('⚡ Malus/Bonus event:', message);
                    onMalusBonus?.(message);
                    break;

                case 'kicked':
                    console.log('❌ Kicked from game:', message.message);
                    setState(prev => ({ ...prev, connected: false }));
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
    }, [onPhraseReceived, onGameStatusChange, onRoundResults, onGameOver, onMalusBonus]);

    // Connect to WebSocket server
    const connect = useCallback(() => {
        const clientId = getClientId();
        const wsUrl = `${serverUrl}/ws/${clientId}`;

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
    }, [serverUrl, getClientId, handleMessage]);

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
        sendMessage({
            type: 'phrase_complete',
            time: timeTaken,
            errors: errorsCount,
            bonus: bonus,
            malus: malus,
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
