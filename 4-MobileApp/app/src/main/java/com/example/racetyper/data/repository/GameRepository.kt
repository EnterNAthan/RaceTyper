package com.example.racetyper.data.repository

import com.example.racetyper.data.model.Friend
import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.websocket.ConnectionState
import com.example.racetyper.data.websocket.GameEvent
import com.example.racetyper.data.websocket.RaceTyperWebSocket
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow

class GameRepository {
    private val webSocket = RaceTyperWebSocket()

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

    // ── Mock data (futur: API REST / BDD) ──

    fun getMockFriends(): List<Friend> {
        return listOf(
            Friend(id = "friend-1", name = "Alexandre", isOnline = true, lastScore = 2450),
            Friend(id = "friend-2", name = "Marie", isOnline = true, lastScore = 1890),
            Friend(id = "friend-3", name = "Thomas", isOnline = false, lastScore = 3200),
            Friend(id = "friend-4", name = "Sophie", isOnline = false, lastScore = 1560),
            Friend(id = "friend-5", name = "Lucas", isOnline = true, lastScore = 2100)
        )
    }
}
