// RaceTyper Admin Interface - JavaScript

class AdminDashboard {
    constructor() {
        this.ws = null;
        this.reconnectInterval = null;
        this.autoScrollLogs = true;
        this.currentEditingPlayer = null;

        this.initializeElements();
        this.attachEventListeners();
        this.connect();
        this.loadInitialData();
    }

    initializeElements() {
        // Status
        this.connectionStatus = document.getElementById('connectionStatus');

        // Game State
        this.currentRound = document.getElementById('currentRound');
        this.playerCount = document.getElementById('playerCount');
        this.gameStatus = document.getElementById('gameStatus');
        this.currentPhrase = document.getElementById('currentPhrase');

        // Players & Ranking
        this.playersList = document.getElementById('playersList');
        this.rankingList = document.getElementById('rankingList');

        // Logs
        this.logsList = document.getElementById('logsList');
        this.autoScrollCheckbox = document.getElementById('autoScrollLogs');

        // Stats
        this.statFinished = document.getElementById('statFinished');
        this.statAvgTime = document.getElementById('statAvgTime');
        this.statTotalErrors = document.getElementById('statTotalErrors');
        this.statBonuses = document.getElementById('statBonuses');

        // Phrases
        this.phrasesList = document.getElementById('phrasesList');
        this.newPhraseInput = document.getElementById('newPhraseInput');

        // Modals
        this.broadcastModal = document.getElementById('broadcastModal');
        this.scoreModal = document.getElementById('scoreModal');
    }

    attachEventListeners() {
        // Control buttons
        document.getElementById('btnStartGame').addEventListener('click', () => this.startGame());
        document.getElementById('btnPauseGame').addEventListener('click', () => this.pauseGame());
        document.getElementById('btnResetGame').addEventListener('click', () => this.resetGame());
        document.getElementById('btnNextRound').addEventListener('click', () => this.nextRound());
        document.getElementById('btnEndGame').addEventListener('click', () => this.endGame());

        // Quick actions
        document.getElementById('btnBroadcastMessage').addEventListener('click', () => this.showBroadcastModal());
        document.getElementById('btnResetScores').addEventListener('click', () => this.resetScores());
        document.getElementById('btnKickAll').addEventListener('click', () => this.kickAllPlayers());
        document.getElementById('btnExportStats').addEventListener('click', () => this.exportStats());

        // Logs
        document.getElementById('btnClearLogs').addEventListener('click', () => this.clearLogs());
        this.autoScrollCheckbox.addEventListener('change', (e) => {
            this.autoScrollLogs = e.target.checked;
        });

        // Phrases
        document.getElementById('btnAddPhrase').addEventListener('click', () => this.addPhrase());

        // Modals
        document.getElementById('btnSendBroadcast').addEventListener('click', () => this.sendBroadcast());
        document.getElementById('btnCancelBroadcast').addEventListener('click', () => this.hideBroadcastModal());
        document.getElementById('btnSaveScore').addEventListener('click', () => this.saveScore());
        document.getElementById('btnCancelScore').addEventListener('click', () => this.hideScoreModal());

        // Close modals on background click
        this.broadcastModal.addEventListener('click', (e) => {
            if (e.target === this.broadcastModal) this.hideBroadcastModal();
        });
        this.scoreModal.addEventListener('click', (e) => {
            if (e.target === this.scoreModal) this.hideScoreModal();
        });
    }

    // WebSocket Connection
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/admin-dashboard`;

        this.addLog('Connexion au serveur...', 'server-info');

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.onConnect();
        };

        this.ws.onmessage = (event) => {
            this.onMessage(event);
        };

        this.ws.onclose = () => {
            this.onDisconnect();
        };

        this.ws.onerror = (error) => {
            this.addLog('Erreur WebSocket: ' + error, 'server-error');
        };
    }

    onConnect() {
        this.connectionStatus.textContent = 'Connecté';
        this.connectionStatus.className = 'status connected';
        this.addLog('Connecté au serveur arbitre', 'server-info');

        if (this.reconnectInterval) {
            clearInterval(this.reconnectInterval);
            this.reconnectInterval = null;
        }

        // Request initial state
        this.sendCommand('get_state');
    }

    onDisconnect() {
        this.connectionStatus.textContent = 'Déconnecté';
        this.connectionStatus.className = 'status disconnected';
        this.addLog('Déconnecté du serveur', 'server-error');

        // Attempt reconnection
        if (!this.reconnectInterval) {
            this.reconnectInterval = setInterval(() => {
                this.addLog('Tentative de reconnexion...', 'server-info');
                this.connect();
            }, 3000);
        }
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
        } catch (error) {
            console.error('Error parsing message:', error);
        }
    }

    handleServerMessage(data) {
        this.addLog(`← ${data.type}`, 'ws-in');

        switch (data.type) {
            case 'state_update':
                this.updateGameState(data);
                break;
            case 'players_update':
                this.updatePlayers(data.players, data.scores);
                break;
            case 'ranking_update':
                this.updateRanking(data.ranking);
                break;
            case 'log':
                this.addLog(data.message, data.level);
                break;
            case 'round_stats':
                this.updateRoundStats(data.stats);
                break;
            case 'phrases_list':
                this.updatePhrasesList(data.phrases, data.current_index);
                break;
            default:
                console.log('Unknown message type:', data);
        }
    }

    sendCommand(command, params = {}) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = { command, ...params };
            this.ws.send(JSON.stringify(message));
            this.addLog(`→ ${command}`, 'ws-out');
        } else {
            this.addLog('Non connecté au serveur', 'server-error');
        }
    }

    // Load initial data via REST API
    async loadInitialData() {
        try {
            const response = await fetch('/api/admin/state');
            if (response.ok) {
                const data = await response.json();
                this.updateGameState(data);
                this.updatePlayers(data.players, data.scores);
                this.updatePhrasesList(data.phrases, data.current_phrase_index);
            }
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    // Update UI
    updateGameState(data) {
        if (data.current_round !== undefined) {
            this.currentRound.textContent = `${data.current_round + 1} / 5`;
        }

        if (data.player_count !== undefined) {
            this.playerCount.textContent = data.player_count;
        }

        if (data.game_status) {
            this.gameStatus.textContent = data.game_status;
            this.gameStatus.className = 'value badge';
        }

        if (data.current_phrase) {
            this.currentPhrase.textContent = data.current_phrase;
        }
    }

    updatePlayers(players, scores) {
        if (!players || Object.keys(players).length === 0) {
            this.playersList.innerHTML = '<p class="empty-state">Aucun joueur connecté</p>';
            return;
        }

        this.playersList.innerHTML = '';

        for (const [playerId] of Object.entries(players)) {
            const score = scores[playerId] || 0;
            const playerDiv = document.createElement('div');
            playerDiv.className = 'player-item';
            playerDiv.innerHTML = `
                <div class="player-info">
                    <div class="player-name">${playerId}</div>
                    <div class="player-score">${score} points</div>
                </div>
                <div class="player-actions">
                    <button class="btn btn-small btn-warning" onclick="dashboard.editPlayerScore('${playerId}')">Score</button>
                    <button class="btn btn-small btn-danger" onclick="dashboard.kickPlayer('${playerId}')">Kick</button>
                </div>
            `;
            this.playersList.appendChild(playerDiv);
        }
    }

    updateRanking(ranking) {
        if (!ranking || ranking.length === 0) {
            this.rankingList.innerHTML = '<p class="empty-state">En attente de scores</p>';
            return;
        }

        this.rankingList.innerHTML = '';

        ranking.forEach((player, index) => {
            const rankDiv = document.createElement('div');
            rankDiv.className = 'rank-item';

            let positionClass = '';
            if (index === 0) positionClass = 'gold';
            else if (index === 1) positionClass = 'silver';
            else if (index === 2) positionClass = 'bronze';

            const medal = `#${index + 1}`;

            rankDiv.innerHTML = `
                <div class="rank-position ${positionClass}">${medal}</div>
                <div class="rank-info">
                    <div class="rank-name">${player.client_id || player.name}</div>
                    <div class="rank-score">${player.score} points</div>
                </div>
            `;
            this.rankingList.appendChild(rankDiv);
        });
    }

    updateRoundStats(stats) {
        this.statFinished.textContent = `${stats.finished}/${stats.total}`;
        this.statAvgTime.textContent = stats.avg_time ? `${stats.avg_time.toFixed(2)}s` : '-';
        this.statTotalErrors.textContent = stats.total_errors || '-';
        this.statBonuses.textContent = stats.bonuses || '-';
    }

    updatePhrasesList(phrases, currentIndex) {
        if (!phrases || phrases.length === 0) {
            this.phrasesList.innerHTML = '<p class="empty-state">Aucune phrase</p>';
            return;
        }

        this.phrasesList.innerHTML = '';

        phrases.forEach((phrase, index) => {
            const phraseDiv = document.createElement('div');
            phraseDiv.className = 'phrase-item' + (index === currentIndex ? ' current' : '');
            phraseDiv.innerHTML = `
                <span class="phrase-text-item">${index + 1}. ${phrase}</span>
                <div class="phrase-actions">
                    <button class="btn btn-small btn-danger" onclick="dashboard.deletePhrase(${index})">×</button>
                </div>
            `;
            this.phrasesList.appendChild(phraseDiv);
        });
    }

    addLog(message, type = 'server-info') {
        const timestamp = new Date().toLocaleTimeString('fr-FR', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        const logDiv = document.createElement('div');
        logDiv.className = `log-entry ${type}`;
        logDiv.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> ${message}`;

        this.logsList.appendChild(logDiv);

        if (this.autoScrollLogs) {
            this.logsList.scrollTop = this.logsList.scrollHeight;
        }

        // Limit logs to 500 entries
        while (this.logsList.children.length > 500) {
            this.logsList.removeChild(this.logsList.firstChild);
        }
    }

    clearLogs() {
        this.logsList.innerHTML = '';
        this.addLog('Logs effacés', 'server-info');
    }

    // Game Control Actions
    startGame() {
        if (confirm('Démarrer une nouvelle partie ?')) {
            this.sendCommand('start_game');
        }
    }

    pauseGame() {
        this.sendCommand('pause_game');
    }

    resetGame() {
        if (confirm('Réinitialiser complètement le jeu ? Tous les scores seront perdus.')) {
            this.sendCommand('reset_game');
        }
    }

    nextRound() {
        if (confirm('Passer à la manche suivante ?')) {
            this.sendCommand('next_round');
        }
    }

    endGame() {
        if (confirm('Terminer la partie immédiatement ?')) {
            this.sendCommand('end_game');
        }
    }

    // Player Actions
    kickPlayer(playerId) {
        if (confirm(`Expulser le joueur ${playerId} ?`)) {
            this.sendCommand('kick_player', { player_id: playerId });
        }
    }

    editPlayerScore(playerId) {
        this.currentEditingPlayer = playerId;
        document.getElementById('scoreModalPlayer').textContent = playerId;
        document.getElementById('scoreModalInput').value = '';
        this.scoreModal.classList.add('active');
    }

    saveScore() {
        const newScore = parseInt(document.getElementById('scoreModalInput').value);
        if (isNaN(newScore)) {
            alert('Score invalide');
            return;
        }

        this.sendCommand('set_score', {
            player_id: this.currentEditingPlayer,
            score: newScore
        });

        this.hideScoreModal();
    }

    hideScoreModal() {
        this.scoreModal.classList.remove('active');
        this.currentEditingPlayer = null;
    }

    // Quick Actions
    showBroadcastModal() {
        document.getElementById('broadcastMessage').value = '';
        this.broadcastModal.classList.add('active');
    }

    hideBroadcastModal() {
        this.broadcastModal.classList.remove('active');
    }

    sendBroadcast() {
        const message = document.getElementById('broadcastMessage').value.trim();
        if (!message) {
            alert('Message vide');
            return;
        }

        this.sendCommand('broadcast_message', { message });
        this.hideBroadcastModal();
    }

    resetScores() {
        if (confirm('Remettre tous les scores à zéro ?')) {
            this.sendCommand('reset_scores');
        }
    }

    kickAllPlayers() {
        if (confirm('Expulser TOUS les joueurs ?')) {
            this.sendCommand('kick_all');
        }
    }

    async exportStats() {
        try {
            const response = await fetch('/api/admin/export');
            if (response.ok) {
                const data = await response.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `racetyper-stats-${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);
                this.addLog('Statistiques exportées', 'server-info');
            }
        } catch (error) {
            this.addLog('Erreur export: ' + error, 'server-error');
        }
    }

    // Phrase Management
    addPhrase() {
        const phrase = this.newPhraseInput.value.trim();
        if (!phrase) {
            alert('Phrase vide');
            return;
        }

        this.sendCommand('add_phrase', { phrase });
        this.newPhraseInput.value = '';
    }

    deletePhrase(index) {
        if (confirm('Supprimer cette phrase ?')) {
            this.sendCommand('delete_phrase', { index });
        }
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new AdminDashboard();
});
