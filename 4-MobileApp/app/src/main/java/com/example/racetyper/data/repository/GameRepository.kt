package com.example.racetyper.data.repository

import com.example.racetyper.data.model.Friend
import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.websocket.ConnectionState
import com.example.racetyper.data.websocket.RaceTyperWebSocket
import kotlinx.coroutines.flow.StateFlow

class GameRepository {
    private val webSocket = RaceTyperWebSocket()

    val connectionState: StateFlow<ConnectionState> = webSocket.connectionState
    val gameState: StateFlow<GameState> = webSocket.gameState
    val scores: StateFlow<Map<String, Int>> = webSocket.scores
    val lastRoundClassement: StateFlow<RoundClassement?> = webSocket.lastRoundClassement

    fun connect(serverUrl: String) {
        webSocket.connect(serverUrl)
    }

    fun disconnect() {
        webSocket.disconnect()
    }

    // Mock friends data for demo
    fun getMockFriends(): List<Friend> {
        return listOf(
            Friend(
                id = "friend-1",
                name = "Alexandre",
                isOnline = true,
                lastScore = 2450
            ),
            Friend(
                id = "friend-2",
                name = "Marie",
                isOnline = true,
                lastScore = 1890
            ),
            Friend(
                id = "friend-3",
                name = "Thomas",
                isOnline = false,
                lastScore = 3200
            ),
            Friend(
                id = "friend-4",
                name = "Sophie",
                isOnline = false,
                lastScore = 1560
            ),
            Friend(
                id = "friend-5",
                name = "Lucas",
                isOnline = true,
                lastScore = 2100
            )
        )
    }
}
