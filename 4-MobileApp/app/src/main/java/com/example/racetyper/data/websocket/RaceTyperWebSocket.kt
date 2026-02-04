package com.example.racetyper.data.websocket

import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.GameStatus
import com.example.racetyper.data.model.Player
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.model.RoundResult
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

sealed class ConnectionState {
    object Disconnected : ConnectionState()
    object Connecting : ConnectionState()
    object Connected : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}

class RaceTyperWebSocket {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(30, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private var webSocket: WebSocket? = null

    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _gameState = MutableStateFlow(GameState())
    val gameState: StateFlow<GameState> = _gameState.asStateFlow()

    private val _lastRoundClassement = MutableStateFlow<RoundClassement?>(null)
    val lastRoundClassement: StateFlow<RoundClassement?> = _lastRoundClassement.asStateFlow()

    private val _scores = MutableStateFlow<Map<String, Int>>(emptyMap())
    val scores: StateFlow<Map<String, Int>> = _scores.asStateFlow()

    fun connect(serverUrl: String, clientId: String = "mobile-spectator") {
        if (_connectionState.value == ConnectionState.Connected ||
            _connectionState.value == ConnectionState.Connecting) {
            return
        }

        _connectionState.value = ConnectionState.Connecting

        val wsUrl = if (serverUrl.startsWith("ws://") || serverUrl.startsWith("wss://")) {
            "$serverUrl/ws/$clientId"
        } else {
            "ws://$serverUrl/ws/$clientId"
        }

        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                _connectionState.value = ConnectionState.Connected
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                _connectionState.value = ConnectionState.Disconnected
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                _connectionState.value = ConnectionState.Error(t.message ?: "Connection failed")
            }
        })
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
        _connectionState.value = ConnectionState.Disconnected
    }

    private fun handleMessage(text: String) {
        try {
            val json = gson.fromJson(text, JsonObject::class.java)
            val type = json.get("type")?.asString ?: return

            when (type) {
                "connection_accepted" -> {
                    // Connection confirmed
                }

                "player_update" -> {
                    val scoresJson = json.getAsJsonObject("scores")
                    val newScores = mutableMapOf<String, Int>()
                    scoresJson?.entrySet()?.forEach { entry ->
                        newScores[entry.key] = entry.value.asInt
                    }
                    _scores.value = newScores
                    updatePlayersFromScores(newScores)
                }

                "new_phrase" -> {
                    val phrase = json.get("phrase")?.asString ?: ""
                    val roundNumber = json.get("round_number")?.asInt ?: 0
                    _gameState.value = _gameState.value.copy(
                        currentPhrase = phrase,
                        currentRound = roundNumber,
                        status = GameStatus.PLAYING
                    )
                }

                "round_classement" -> {
                    val classementArray = json.getAsJsonArray("classement")
                    val results = classementArray?.map { element ->
                        val obj = element.asJsonObject
                        RoundResult(
                            rank = obj.get("rank")?.asInt ?: 0,
                            clientId = obj.get("client_id")?.asString ?: "",
                            time = obj.get("time")?.asDouble ?: 0.0,
                            scoreAdded = obj.get("score_added")?.asInt ?: 0
                        )
                    } ?: emptyList()

                    val globalScoresJson = json.getAsJsonObject("global_scores")
                    val globalScores = mutableMapOf<String, Int>()
                    globalScoresJson?.entrySet()?.forEach { entry ->
                        globalScores[entry.key] = entry.value.asInt
                    }

                    _lastRoundClassement.value = RoundClassement(results, globalScores)
                    _scores.value = globalScores
                    updatePlayersFromScores(globalScores)
                }

                "game_over" -> {
                    val finalScoresJson = json.getAsJsonObject("final_scores")
                    val finalScores = mutableMapOf<String, Int>()
                    finalScoresJson?.entrySet()?.forEach { entry ->
                        finalScores[entry.key] = entry.value.asInt
                    }
                    _scores.value = finalScores
                    _gameState.value = _gameState.value.copy(status = GameStatus.FINISHED)
                    updatePlayersFromScores(finalScores)
                }

                "game_paused" -> {
                    _gameState.value = _gameState.value.copy(status = GameStatus.PAUSED)
                }

                "game_reset" -> {
                    _gameState.value = GameState()
                    _scores.value = emptyMap()
                    _lastRoundClassement.value = null
                }

                "state_update" -> {
                    val currentRound = json.get("current_round")?.asInt ?: 0
                    val totalRounds = json.get("total_rounds")?.asInt ?: 5
                    val status = json.get("game_status")?.asString ?: "waiting"
                    val phrase = json.get("current_phrase")?.asString ?: ""

                    val scoresJson = json.getAsJsonObject("scores")
                    val newScores = mutableMapOf<String, Int>()
                    scoresJson?.entrySet()?.forEach { entry ->
                        newScores[entry.key] = entry.value.asInt
                    }
                    _scores.value = newScores

                    _gameState.value = GameState(
                        status = GameStatus.fromString(status),
                        currentRound = currentRound,
                        totalRounds = totalRounds,
                        currentPhrase = phrase,
                        players = newScores.map { (id, score) ->
                            id to Player(id, score, true)
                        }.toMap()
                    )
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun updatePlayersFromScores(scores: Map<String, Int>) {
        val players = scores.map { (id, score) ->
            id to Player(id, score, true)
        }.toMap()
        _gameState.value = _gameState.value.copy(players = players)
    }
}
