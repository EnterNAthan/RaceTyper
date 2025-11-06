import { useState, useEffect, useCallback } from 'react';
import useWebSocket from 'react-use-websocket';

// Configuration URLs
const WEBSOCKET_URL = 'ws://192.168.1.100:8000/ws/game/1/player_1';
const GPIO_SERVICE_URL = 'http://localhost:5001';

function GameInterface() {
  // State management
  const [phraseToType, setPhraseToType] = useState('Le rapide renard brun saute par-dessus le chien paresseux.');
  const [currentInput, setCurrentInput] = useState('');
  const [gameProgress, setGameProgress] = useState('Joueur 1: 0%');

  // Function to trigger local GPIO actions
  const triggerLocalGPIO = async (action) => {
    try {
      const response = await fetch(`${GPIO_SERVICE_URL}/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      console.log('GPIO action result:', data);
    } catch (error) {
      console.error('Error triggering GPIO:', error);
    }
  };

  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(WEBSOCKET_URL, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const message = JSON.parse(lastMessage.data);
        console.log('Received message:', message);

        if (message.type === 'gameStateUpdate') {
          setGameProgress(message.progress || 'Joueur 1: 0%');
        } else if (message.type === 'phraseUpdate') {
          setPhraseToType(message.phrase || '');
        } else if (message.type === 'event' && message.action) {
          triggerLocalGPIO(message.action);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    }
  }, [lastMessage]);

  // Handle input change
  const handleChange = (e) => {
    const value = e.target.value;
    
    // Check if space key was pressed (word completed)
    if (value.endsWith(' ')) {
      const word = value.trim();
      if (word) {
        // Send the completed word via WebSocket
        const message = JSON.stringify({
          type: 'word_completed',
          word: word,
        });
        sendMessage(message);
        console.log('Sent word:', word);
      }
      // Clear the input
      setCurrentInput('');
    } else {
      setCurrentInput(value);
    }
  };

  // Connection status indicator
  const getConnectionStatus = () => {
    const connectionStatus = {
      0: 'CONNECTING',
      1: 'OPEN',
      2: 'CLOSING',
      3: 'CLOSED',
    };
    return connectionStatus[readyState];
  };

  return (
    <div>
      <h1>RaceTyper - Console</h1>
      <p style={{ color: '#39FF14', fontSize: '0.8em' }}>
        WebSocket Status: {getConnectionStatus()}
      </p>
      <h2>{phraseToType}</h2>
      <input
        type="text"
        value={currentInput}
        onChange={handleChange}
        placeholder="Tapez ici..."
        autoFocus
      />
      <h1>{gameProgress}</h1>
    </div>
  );
}

export default GameInterface;
