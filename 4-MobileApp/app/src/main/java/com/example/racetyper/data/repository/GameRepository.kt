package com.example.racetyper.data.repository

import com.example.racetyper.data.model.Friend
import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.MalusPayload
import com.example.racetyper.data.model.MalusType
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.websocket.ConnectionState
import com.example.racetyper.data.websocket.GameEvent
import com.example.racetyper.data.websocket.RaceTyperWebSocket
import com.google.gson.Gson
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow

class GameRepository {
    private val webSocket = RaceTyperWebSocket()
    private val gson = Gson()

    // ── State flows (persistent state consumed by Compose UI) ──

    val connectionState: StateFlow<ConnectionState> = webSocket.connectionState
    val gameState: StateFlow<GameState> = webSocket.gameState
    val scores: StateFlow<Map<String, Int>> = webSocket.scores
    val lastRoundClassement: StateFlow<RoundClassement?> = webSocket.lastRoundClassement

    /** Événements ponctuels (admin_message, kicked, …). Collectés via `collectLatest`. */
    val events: SharedFlow<GameEvent> = webSocket.events

    // ── Connection lifecycle ──

    fun connect(serverUrl: String) {
        webSocket.connect(serverUrl)
    }

    fun disconnect() {
        webSocket.disconnect()
    }

    /** Libère les ressources internes (scope, OkHttp). Appelé depuis ViewModel.onCleared(). */
    fun destroy() {
        webSocket.destroy()
    }

    // ── Game Master: envoi de malus ──

    /**
     * Envoie un malus à un joueur cible via la WebSocket.
     * @return true si le message a pu être envoyé.
     */
    fun sendMalus(targetPlayerId: String, malusType: MalusType): Boolean {
        val payload = MalusPayload(
            targetPlayerId = targetPlayerId,
            malusType = malusType.key
        )
        return webSocket.send(gson.toJson(payload))
    }
}
