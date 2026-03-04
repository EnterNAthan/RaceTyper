package com.example.racetyper.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.racetyper.data.SettingsManager
import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.MalusType
import com.example.racetyper.data.model.Player
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.repository.GameRepository
import com.example.racetyper.data.websocket.ConnectionState
import com.example.racetyper.data.websocket.GameEvent
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * Résultat ponctuel d'un envoi de malus – consommé une seule fois par l'UI.
 */
sealed class MalusSendResult {
    data class Success(val targetId: String, val malusType: MalusType) : MalusSendResult()
    data class Failure(val reason: String) : MalusSendResult()
}

class GameViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = GameRepository()
    private val settingsManager = SettingsManager(application)

    val connectionState: StateFlow<ConnectionState> = repository.connectionState
    val gameState: StateFlow<GameState> = repository.gameState
    val scores: StateFlow<Map<String, Int>> = repository.scores
    val lastRoundClassement: StateFlow<RoundClassement?> = repository.lastRoundClassement

    /** Événements ponctuels — collectés via LaunchedEffect dans Compose. */
    val events: SharedFlow<GameEvent> = repository.events

    val serverUrl: StateFlow<String> = settingsManager.serverUrl
        .stateIn(viewModelScope, SharingStarted.Eagerly, SettingsManager.DEFAULT_SERVER_URL)

    /** Événements ponctuels pour le feedback d'envoi de malus. */
    private val _malusEvents = MutableSharedFlow<MalusSendResult>(extraBufferCapacity = 8)
    val malusEvents: SharedFlow<MalusSendResult> = _malusEvents.asSharedFlow()

    fun connect() {
        repository.connect(serverUrl.value)
    }

    fun connectTo(url: String) {
        viewModelScope.launch {
            settingsManager.setServerUrl(url)
            repository.disconnect()
            repository.connect(url)
        }
    }

    fun disconnect() {
        repository.disconnect()
    }

    fun updateServerUrl(url: String) {
        viewModelScope.launch {
            settingsManager.setServerUrl(url)
        }
    }

    // ── Game Master: envoi de malus ──

    /**
     * Envoie un malus à un joueur cible.
     * Vérifie que la connexion est active avant d'envoyer.
     */
    fun sendMalus(targetPlayerId: String, malusType: MalusType) {
        if (connectionState.value !is ConnectionState.Connected) {
            _malusEvents.tryEmit(MalusSendResult.Failure("Non connecté au serveur"))
            return
        }
        val sent = repository.sendMalus(targetPlayerId, malusType)
        if (sent) {
            _malusEvents.tryEmit(MalusSendResult.Success(targetPlayerId, malusType))
        } else {
            _malusEvents.tryEmit(MalusSendResult.Failure("Échec de l'envoi"))
        }
    }

    // ── Helpers ──

    fun getPlayersSortedByScore(): List<Player> {
        return gameState.value.players.values
            .sortedByDescending { it.score }
    }

    fun getRankingList(): List<Pair<Int, Player>> {
        return getPlayersSortedByScore()
            .mapIndexed { index, player -> (index + 1) to player }
    }

    /**
     * Retourne la liste des joueurs actifs (connectés, hors spectateurs/bot).
     * Utilisée par l'écran de contrôle des joueurs (Game Master).
     */
    fun getActivePlayersForControl(): List<Player> {
        return gameState.value.players.values
            .filter { it.isConnected }
            .filter { !it.clientId.startsWith("mobile") && it.clientId != "BOT-IA" }
            .sortedBy { it.clientId }
    }

    override fun onCleared() {
        super.onCleared()
        repository.destroy()
    }
}
