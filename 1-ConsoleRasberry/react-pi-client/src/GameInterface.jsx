import { useState, useEffect, useCallback, useRef } from 'react';
import useWebSocket from 'react-use-websocket';

// Configuration - Obtenir depuis l'URL ou localStorage
const getClientId = () => {
  // Essayer de récupérer depuis l'URL
  const params = new URLSearchParams(window.location.search);
  const urlClientId = params.get('client');

  if (urlClientId) {
    localStorage.setItem('racetyper_client_id', urlClientId);
    return urlClientId;
  }

  // Sinon, récupérer depuis localStorage ou générer
  const storedId = localStorage.getItem('racetyper_client_id');
  if (storedId) return storedId;

  // Générer un ID unique
  const newId = `player-${Math.random().toString(36).substr(2, 9)}`;
  localStorage.setItem('racetyper_client_id', newId);
  return newId;
};

const CLIENT_ID = getClientId();
const SERVER_URL = 'ws://localhost:8080/ws/' + CLIENT_ID;
const GPIO_SERVICE_URL = 'http://localhost:5001';

function GameInterface() {
  // États du jeu
  const [gameState, setGameState] = useState('connecting'); // connecting, waiting, playing, round_wait, finished
  const [phraseToType, setPhraseToType] = useState('');
  const [words, setWords] = useState([]);
  const [currentWordIndex, setCurrentWordIndex] = useState(0);
  const [currentInput, setCurrentInput] = useState('');
  const [errors, setErrors] = useState(0);
  const [startTime, setStartTime] = useState(null);
  const [scores, setScores] = useState({});
  const [ranking, setRanking] = useState([]);
  const [roundNumber, setRoundNumber] = useState(0);
  const [waitingMessage, setWaitingMessage] = useState('');
  const [finalScores, setFinalScores] = useState({});
  const [objectsTriggered, setObjectsTriggered] = useState([]);

  // Refs
  const inputRef = useRef(null);

  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(SERVER_URL, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  // Fonction pour trigger les GPIO
  const triggerLocalGPIO = async (action) => {
    try {
      // Mapper les actions du serveur vers les endpoints GPIO
      let endpoint = '';
      if (action === 'TRIGGER_SIREN') {
        endpoint = 'siren/on';
        // Éteindre après 2 secondes
        setTimeout(async () => {
          await fetch(`${GPIO_SERVICE_URL}/siren/off`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          });
        }, 2000);
      } else if (action === 'SCREEN_SHAKE') {
        // Effet visuel de shake
        document.body.style.animation = 'shake 0.5s';
        setTimeout(() => {
          document.body.style.animation = '';
        }, 500);
        return;
      } else if (action === 'SLEEP') {
        // Désactiver l'input pendant 3 secondes
        if (inputRef.current) {
          inputRef.current.disabled = true;
          setTimeout(() => {
            if (inputRef.current) inputRef.current.disabled = false;
          }, 3000);
        }
        return;
      } else if (action === 'SWAPKEY') {
        // TODO: Implémenter swap de touches
        console.log('SWAPKEY action received');
        return;
      }

      if (endpoint) {
        await fetch(`${GPIO_SERVICE_URL}/${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
      }
    } catch (error) {
      console.error('Error triggering GPIO:', error);
    }
  };

  // Détecte les bonus/malus dans un mot
  const detectObject = (word, cleanWord) => {
    if (word.match(/\^\^(.+?)\^\^/)) {
      return { type: 'bonus', word: cleanWord };
    }
    if (word.match(/&(.+?)&/)) {
      return { type: 'malus', word: cleanWord };
    }
    return null;
  };

  // Nettoie un mot des marqueurs
  const cleanWord = (word) => {
    return word.replace(/\^\^/g, '').replace(/&/g, '');
  };

  // Handler des messages WebSocket
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const message = JSON.parse(lastMessage.data);
        console.log('📨 Received:', message.type, message);

        switch (message.type) {
          case 'new_phrase':
            // Nouvelle phrase à taper
            setPhraseToType(message.phrase);
            const phraseWords = message.phrase.split(' ');
            setWords(phraseWords);
            setCurrentWordIndex(0);
            setCurrentInput('');
            setErrors(0);
            setObjectsTriggered([]);
            setStartTime(Date.now());
            setGameState('playing');
            setWaitingMessage('');
            if (message.round_number !== undefined) {
              setRoundNumber(message.round_number);
            }
            break;

          case 'player_update':
            // Mise à jour des scores
            setScores(message.scores || {});
            if (gameState === 'waiting') {
              setGameState('waiting');
            }
            break;

          case 'round_wait':
            // En attente des autres joueurs
            setGameState('round_wait');
            setWaitingMessage(message.message || 'En attente des autres joueurs...');
            break;

          case 'round_classement':
            // Affichage du classement de la manche
            setRanking(message.classement || []);
            setScores(message.global_scores || {});
            setGameState('round_wait');
            setWaitingMessage('Classement de la manche');
            break;

          case 'game_over':
            // Fin du jeu
            setFinalScores(message.final_scores || {});
            setGameState('finished');
            break;

          case 'hardware_action':
            // Action hardware (malus reçu)
            if (message.action) {
              triggerLocalGPIO(message.action);
            }
            break;

          case 'kicked':
            // Joueur expulsé
            alert(message.message || 'Vous avez été expulsé');
            setGameState('waiting');
            break;

          case 'game_paused':
          case 'game_reset':
          case 'admin_message':
            // Messages de l'arbitre
            alert(message.message);
            if (message.type === 'game_reset') {
              setGameState('waiting');
              setScores({});
              setCurrentWordIndex(0);
              setErrors(0);
            }
            break;

          default:
            console.log('Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    }
  }, [lastMessage]);

  // Handler de changement d'input
  const handleChange = (e) => {
    if (gameState !== 'playing') return;

    const value = e.target.value;

    // Si espace pressé, valider le mot
    if (value.endsWith(' ')) {
      const typedWord = value.trim();
      if (!typedWord) {
        setCurrentInput('');
        return;
      }

      // Récupérer le mot attendu
      const expectedWord = words[currentWordIndex];
      const cleanExpected = cleanWord(expectedWord);

      // Vérifier si c'est correct
      const isCorrect = typedWord.toLowerCase() === cleanExpected.toLowerCase();

      if (!isCorrect) {
        setErrors(prev => prev + 1);
      }

      // Détecter bonus/malus
      const obj = detectObject(expectedWord, cleanExpected);
      if (obj && isCorrect) {
        setObjectsTriggered(prev => [...prev, { ...obj, success: true }]);
      }

      // Passer au mot suivant
      const nextIndex = currentWordIndex + 1;
      setCurrentWordIndex(nextIndex);
      setCurrentInput('');

      // Si c'est le dernier mot, envoyer le résultat
      if (nextIndex >= words.length) {
        sendPhraseFinished();
      }
    } else {
      setCurrentInput(value);
    }
  };

  // Envoyer le résultat au serveur
  const sendPhraseFinished = () => {
    const timeTaken = (Date.now() - startTime) / 1000; // en secondes

    const message = {
      action: 'phrase_finished',
      time_taken: timeTaken,
      errors: errors,
      objects_triggered: objectsTriggered
    };

    console.log('📤 Sending:', message);
    sendMessage(JSON.stringify(message));

    // Réinitialiser pour la prochaine manche
    setStartTime(null);
  };

  // Status de connexion
  const getConnectionStatus = () => {
    const status = {
      0: '🔄 CONNEXION...',
      1: '✅ CONNECTÉ',
      2: '⏳ FERMETURE...',
      3: '❌ DÉCONNECTÉ',
    };
    return status[readyState];
  };

  // Afficher le mot courant avec highlight
  const renderWords = () => {
    return words.map((word, index) => {
      const cleanedWord = cleanWord(word);
      const isBonus = word.includes('^^');
      const isMalus = word.includes('&');
      const isCurrent = index === currentWordIndex;
      const isPast = index < currentWordIndex;

      let style = {
        display: 'inline-block',
        margin: '0 8px',
        padding: '4px 8px',
        borderRadius: '4px',
        transition: 'all 0.3s ease',
      };

      if (isCurrent) {
        style.backgroundColor = '#39FF14';
        style.color = '#000';
        style.fontWeight = 'bold';
        style.transform = 'scale(1.2)';
      } else if (isPast) {
        style.opacity = '0.5';
        style.textDecoration = 'line-through';
      }

      if (isBonus) {
        style.border = '2px solid gold';
      } else if (isMalus) {
        style.border = '2px solid red';
      }

      return (
        <span key={index} style={style}>
          {cleanedWord}
        </span>
      );
    });
  };

  // Affichage du classement
  const renderRanking = () => {
    if (ranking.length === 0) return null;

    return (
      <div style={{ margin: '20px 0' }}>
        <h3>🏆 Classement de la manche</h3>
        {ranking.map((player, index) => {
          const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`;
          const isMe = player.client_id === CLIENT_ID;

          return (
            <div
              key={player.client_id}
              style={{
                padding: '10px',
                margin: '5px 0',
                backgroundColor: isMe ? '#39FF14' : 'rgba(57, 255, 20, 0.1)',
                color: isMe ? '#000' : '#39FF14',
                borderRadius: '5px',
                fontWeight: isMe ? 'bold' : 'normal'
              }}
            >
              {medal} {player.client_id} - {player.time?.toFixed(2)}s - +{player.score_added} points
            </div>
          );
        })}
      </div>
    );
  };

  // Affichage des scores
  const renderScores = () => {
    const sortedScores = Object.entries(scores).sort((a, b) => b[1] - a[1]);

    return (
      <div style={{ marginTop: '20px', fontSize: '0.9em' }}>
        <h4>📊 Scores Globaux:</h4>
        {sortedScores.map(([playerId, score]) => {
          const isMe = playerId === CLIENT_ID;
          return (
            <div key={playerId} style={{
              color: isMe ? '#FFD700' : '#39FF14',
              fontWeight: isMe ? 'bold' : 'normal'
            }}>
              {isMe ? '➤ ' : ''}{playerId}: {score} points
            </div>
          );
        })}
      </div>
    );
  };

  // Affichage principal selon l'état
  const renderGameScreen = () => {
    if (gameState === 'connecting') {
      return (
        <div>
          <h1>🔄 Connexion au serveur...</h1>
          <p>ID: {CLIENT_ID}</p>
        </div>
      );
    }

    if (gameState === 'waiting') {
      return (
        <div>
          <h1>⏳ En attente</h1>
          <p>En attente du démarrage de la partie...</p>
          <p style={{ fontSize: '0.8em', marginTop: '20px' }}>Votre ID: {CLIENT_ID}</p>
          {Object.keys(scores).length > 0 && renderScores()}
        </div>
      );
    }

    if (gameState === 'playing') {
      const progress = words.length > 0 ? Math.round((currentWordIndex / words.length) * 100) : 0;
      const timeElapsed = startTime ? ((Date.now() - startTime) / 1000).toFixed(1) : 0;

      return (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h3>Manche {roundNumber + 1}/5</h3>
              <p>⏱ {timeElapsed}s | ❌ {errors} erreurs</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <h3>Score: {scores[CLIENT_ID] || 0}</h3>
              <p>{progress}% complété</p>
            </div>
          </div>

          <div style={{
            fontSize: '1.5em',
            lineHeight: '2em',
            marginBottom: '30px',
            minHeight: '150px',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            alignItems: 'center'
          }}>
            {renderWords()}
          </div>

          <input
            ref={inputRef}
            type="text"
            value={currentInput}
            onChange={handleChange}
            placeholder="Tapez le mot en vert..."
            autoFocus
            style={{
              fontSize: '1.5em',
              padding: '15px',
              width: '80%',
              maxWidth: '600px'
            }}
          />

          {Object.keys(scores).length > 1 && (
            <div style={{ marginTop: '30px', fontSize: '0.9em' }}>
              <h4>Autres joueurs:</h4>
              {Object.entries(scores).map(([playerId, score]) => {
                if (playerId === CLIENT_ID) return null;
                return (
                  <div key={playerId}>
                    {playerId}: {score} points
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    if (gameState === 'round_wait') {
      return (
        <div>
          <h1>⏳ {waitingMessage}</h1>
          {renderRanking()}
          {renderScores()}
        </div>
      );
    }

    if (gameState === 'finished') {
      const sortedFinalScores = Object.entries(finalScores).sort((a, b) => b[1] - a[1]);
      const myPosition = sortedFinalScores.findIndex(([id]) => id === CLIENT_ID) + 1;

      return (
        <div>
          <h1>🏁 PARTIE TERMINÉE!</h1>

          {myPosition === 1 && <h2 style={{ color: '#FFD700', fontSize: '3em' }}>🥇 VICTOIRE! 🥇</h2>}
          {myPosition === 2 && <h2 style={{ color: '#C0C0C0', fontSize: '2.5em' }}>🥈 2ème Place! 🥈</h2>}
          {myPosition === 3 && <h2 style={{ color: '#CD7F32', fontSize: '2em' }}>🥉 3ème Place! 🥉</h2>}
          {myPosition > 3 && <h2>Position: {myPosition}ème</h2>}

          <div style={{ marginTop: '30px' }}>
            <h3>🏆 Classement Final:</h3>
            {sortedFinalScores.map(([playerId, score], index) => {
              const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`;
              const isMe = playerId === CLIENT_ID;

              return (
                <div
                  key={playerId}
                  style={{
                    padding: '15px',
                    margin: '10px 0',
                    backgroundColor: isMe ? '#39FF14' : 'rgba(57, 255, 20, 0.1)',
                    color: isMe ? '#000' : '#39FF14',
                    borderRadius: '5px',
                    fontSize: '1.2em',
                    fontWeight: isMe ? 'bold' : 'normal'
                  }}
                >
                  {medal} {playerId} - {score} points
                </div>
              );
            })}
          </div>

          <p style={{ marginTop: '40px', fontSize: '0.9em' }}>
            En attente de la prochaine partie...
          </p>
        </div>
      );
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <h1 style={{ margin: 0 }}>🏁 RaceTyper</h1>
        <p style={{
          color: readyState === 1 ? '#39FF14' : '#FF3914',
          fontSize: '0.8em',
          margin: 0
        }}>
          {getConnectionStatus()}
        </p>
      </div>

      {renderGameScreen()}
    </div>
  );
}

export default GameInterface;
