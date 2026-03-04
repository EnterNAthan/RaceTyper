package com.example.racetyper.data.websocket

import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.GameStatus
import com.example.racetyper.data.model.Player
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.model.RoundResult
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit
import kotlin.math.min

// ──────────────────────────────── Connection state ────────────────────────────

sealed class ConnectionState {
    data object Disconnected : ConnectionState()
    data object Connecting : ConnectionState()
    data object Connected : ConnectionState()
    data class Reconnecting(val attempt: Int) : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}

// ──────────────────────────────── Transient events ───────────────────────────

/** Events ponctuels consommés une seule fois par l'UI (SharedFlow). */
sealed class GameEvent {
    data class AdminMessage(val message: String) : GameEvent()
    data class Kicked(val reason: String) : GameEvent()
    data class RoundWait(val message: String) : GameEvent()
    data class ConnectionAccepted(val clientId: String) : GameEvent()
}

// ──────────────────────────────── WebSocket client ───────────────────────────

class RaceTyperWebSocket {

    companion object {
        private const val TAG = "RaceTyperWS"
        private const val INITIAL_BACKOFF_MS = 1_000L
        private const val MAX_BACKOFF_MS = 30_000L
        private const val NORMAL_CLOSE_CODE = 1000
    }

    // OkHttp — un seul client partagé, with ping keep-alive
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    private val gson = Gson()
    private var webSocket: WebSocket? = null

    // Reconnection bookkeeping
    private var serverUrl: String = ""
    private var clientId: String = "mobile-spectator"
    private var reconnectAttempt = 0
    private var reconnectJob: Job? = null
    private var manualDisconnect = false

    // Coroutine scope tied to the WebSocket lifecycle
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    // ── Exposed state ──

    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _gameState = MutableStateFlow(GameState())
    val gameState: StateFlow<GameState> = _gameState.asStateFlow()

    private val _lastRoundClassement = MutableStateFlow<RoundClassement?>(null)
    val lastRoundClassement: StateFlow<RoundClassement?> = _lastRoundClassement.asStateFlow()

    private val _scores = MutableStateFlow<Map<String, Int>>(emptyMap())
    val scores: StateFlow<Map<String, Int>> = _scores.asStateFlow()

    /** Événements ponctuels (admin_message, kicked, …). replay=0  → pas de cache. */
    private val _events = MutableSharedFlow<GameEvent>(extraBufferCapacity = 16)
    val events: SharedFlow<GameEvent> = _events.asSharedFlow()

    // ── Public API ──

    /**
     * Ouvre la connexion WebSocket vers le serveur.
     * Si déjà connecté ou en cours, l'appel est ignoré.
     */
    fun connect(serverUrl: String, clientId: String = "mobile-spectator") {
        if (_connectionState.value is ConnectionState.Connected ||
            _connectionState.value is ConnectionState.Connecting
        ) return

        this.serverUrl = serverUrl
        this.clientId = clientId
        this.manualDisconnect = false
        this.reconnectAttempt = 0

        openSocket()
    }

    /** Ferme proprement la connexion et stoppe la reconnexion automatique. */
    fun disconnect() {
        manualDisconnect = true
        reconnectJob?.cancel()
        reconnectJob = null
        webSocket?.close(NORMAL_CLOSE_CODE, "User disconnected")
        webSocket = null
        _connectionState.value = ConnectionState.Disconnected
    }

    /**
     * Envoie un message JSON brut au serveur via la WebSocket ouverte.
     * @return true si le message a été mis en file d'envoi, false si la connexion est fermée.
     */
    fun send(json: String): Boolean {
        return webSocket?.send(json) ?: false
    }

    /** Libère toutes les ressources (à appeler quand le Repository est détruit). */
    fun destroy() {
        disconnect()
        scope.cancel()
    }

    // ── Internal: open / reconnect ──

    private fun openSocket() {
        _connectionState.value = if (reconnectAttempt == 0)
            ConnectionState.Connecting
        else
            ConnectionState.Reconnecting(reconnectAttempt)

        val wsUrl = buildWsUrl(serverUrl, clientId)
        val request = Request.Builder().url(wsUrl).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {

            override fun onOpen(webSocket: WebSocket, response: Response) {
                reconnectAttempt = 0
                _connectionState.value = ConnectionState.Connected
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(NORMAL_CLOSE_CODE, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                handleDisconnect("Closed: $reason")
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                handleDisconnect(t.message ?: "Connection failed")
            }
        })
    }

    private fun handleDisconnect(reason: String) {
        webSocket = null
        if (manualDisconnect) {
            _connectionState.value = ConnectionState.Disconnected
            return
        }
        _connectionState.value = ConnectionState.Error(reason)
        scheduleReconnect()
    }

    private fun scheduleReconnect() {
        reconnectJob?.cancel()
        reconnectJob = scope.launch {
            reconnectAttempt++
            val delayMs = min(INITIAL_BACKOFF_MS * (1L shl (reconnectAttempt - 1)), MAX_BACKOFF_MS)
            delay(delayMs)
            if (!manualDisconnect) openSocket()
        }
    }

    private fun buildWsUrl(raw: String, id: String): String {
        val base = when {
            raw.startsWith("ws://") || raw.startsWith("wss://") -> raw
            else -> "ws://$raw"
        }
        return "${base.trimEnd('/')}/ws/$id"
    }

    // ── Message routing ──

    private fun handleMessage(text: String) {
        try {
            val json = gson.fromJson(text, JsonObject::class.java)
            val type = json.get("type")?.asString ?: return

            when (type) {
                // ─── Connexion ───
                "connection_accepted" -> {
                    val id = json.get("client_id")?.asString ?: clientId
                    _events.tryEmit(GameEvent.ConnectionAccepted(id))
                }

                // ─── État initial (envoyé quand le jeu n'est pas "playing") ───
                "game_status" -> {
                    val status = json.get("status")?.asString ?: "waiting"
                    _gameState.value = _gameState.value.copy(
                        status = GameStatus.fromString(status)
                    )
                }

                // ─── Scores / joueurs ───
                "player_update" -> {
                    val newScores = parseScores(json.getAsJsonObject("scores"))
                    _scores.value = newScores
                    updatePlayersFromScores(newScores)
                }

                // ─── Nouvelle manche ───
                "new_phrase" -> {
                    val phrase = json.get("phrase")?.asString ?: ""
                    val roundNumber = json.get("round_number")?.asInt ?: 0
                    _gameState.value = _gameState.value.copy(
                        currentPhrase = phrase,
                        currentRound = roundNumber,
                        status = GameStatus.PLAYING
                    )
                }

                // ─── Classement de fin de manche ───
                "round_classement" -> {
                    val results = json.getAsJsonArray("classement")?.map { el ->
                        val obj = el.asJsonObject
                        RoundResult(
                            rank = obj.get("rank")?.asInt ?: 0,
                            clientId = obj.get("client_id")?.asString ?: "",
                            time = obj.get("time")?.asDouble ?: 0.0,
                            scoreAdded = obj.get("score_added")?.asInt ?: 0
                        )
                    } ?: emptyList()

                    val globalScores = parseScores(json.getAsJsonObject("global_scores"))
                    _lastRoundClassement.value = RoundClassement(results, globalScores)
                    _scores.value = globalScores
                    updatePlayersFromScores(globalScores)
                }

                // ─── Fin de partie ───
                "game_over" -> {
                    val finalScores = parseScores(json.getAsJsonObject("final_scores"))
                    _scores.value = finalScores
                    _gameState.value = _gameState.value.copy(status = GameStatus.GAME_OVER)
                    updatePlayersFromScores(finalScores)
                }

                // ─── Pause ───
                "game_paused" -> {
                    _gameState.value = _gameState.value.copy(status = GameStatus.PAUSED)
                }

                // ─── Reset ───
                "game_reset" -> {
                    _gameState.value = GameState()
                    _scores.value = emptyMap()
                    _lastRoundClassement.value = null
                }

                // ─── State complet (admin push ou réponse get_state) ───
                "state_update" -> {
                    val currentRound = json.get("current_round")?.asInt ?: 0
                    val totalRounds = json.get("total_rounds")?.asInt ?: 5
                    val status = json.get("game_status")?.asString ?: "waiting"
                    val phrase = json.get("current_phrase")?.asString ?: ""
                    val newScores = parseScores(json.getAsJsonObject("scores"))

                    _scores.value = newScores
                    _gameState.value = GameState(
                        status = GameStatus.fromString(status),
                        currentRound = currentRound,
                        totalRounds = totalRounds,
                        currentPhrase = phrase,
                        players = buildPlayers(newScores)
                    )
                }

                // ─── Attente fin de manche (spectateur) ───
                "round_wait" -> {
                    val msg = json.get("message")?.asString ?: ""
                    _events.tryEmit(GameEvent.RoundWait(msg))
                }

                // ─── Message admin broadcast ───
                "admin_message" -> {
                    val msg = json.get("message")?.asString ?: ""
                    _events.tryEmit(GameEvent.AdminMessage(msg))
                }

                // ─── Expulsion ───
                "kicked" -> {
                    val msg = json.get("message")?.asString ?: "Expulsé"
                    manualDisconnect = true          // ne pas auto-reconnecter
                    _events.tryEmit(GameEvent.Kicked(msg))
                    _connectionState.value = ConnectionState.Disconnected
                }
            }
        } catch (_: Exception) {
            // Malformed JSON — ignoré silencieusement
        }
    }

    // ── Helpers ──

    private fun parseScores(obj: JsonObject?): Map<String, Int> {
        val map = mutableMapOf<String, Int>()
        obj?.entrySet()?.forEach { (key, value) ->
            map[key] = value.asInt
        }
        return map
    }

    private fun buildPlayers(scores: Map<String, Int>): Map<String, Player> =
        scores.map { (id, score) -> id to Player(id, score, true) }.toMap()

    private fun updatePlayersFromScores(scores: Map<String, Int>) {
        _gameState.value = _gameState.value.copy(players = buildPlayers(scores))
    }
}