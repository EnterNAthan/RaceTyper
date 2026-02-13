package com.example.racetyper.data.model

import com.google.gson.annotations.SerializedName

/**
 * Modèles partagés avec le serveur arbitre (contrat API JSON snake_case).
 * Alignés avec 2-ServerArbiter (WebSocket + REST) et la BDD PostgreSQL.
 */

data class Player(
    val clientId: String,
    val score: Int = 0,
    val isConnected: Boolean = true
)

data class GameState(
    val status: GameStatus = GameStatus.WAITING,
    val currentRound: Int = 0,
    val totalRounds: Int = 5,
    val currentPhrase: String = "",
    val players: Map<String, Player> = emptyMap()
)

enum class GameStatus {
    WAITING,
    PLAYING,
    PAUSED,
    FINISHED;

    companion object {
        fun fromString(value: String): GameStatus {
            return when (value.lowercase()) {
                "waiting" -> WAITING
                "playing" -> PLAYING
                "paused" -> PAUSED
                "finished" -> FINISHED
                else -> WAITING
            }
        }
    }
}

/** Aligné avec le message WebSocket round_classement (rank, client_id, time, score_added). */
data class RoundResult(
    val rank: Int,
    @SerializedName("client_id") val clientId: String,
    val time: Double,
    @SerializedName("score_added") val scoreAdded: Int
)

/** Aligné avec le message WebSocket round_classement (classement, global_scores). */
data class RoundClassement(
    val classement: List<RoundResult>,
    @SerializedName("global_scores") val globalScores: Map<String, Int>
)

/** Ami (mock ou futur joueur persisté depuis l’API). */
data class Friend(
    val id: String,
    val name: String,
    val avatarUrl: String? = null,
    val isOnline: Boolean = false,
    val lastScore: Int = 0
)

// ---------- DTOs pour les API REST basées sur la BDD (futur) ----------

/** Résumé d’une partie passée (GET /api/games ou /api/history). */
data class GameSummary(
    val id: String,
    val status: String,
    @SerializedName("started_at") val startedAt: Long? = null,
    @SerializedName("ended_at") val endedAt: Long? = null,
    @SerializedName("total_rounds") val totalRounds: Int = 0,
    @SerializedName("final_scores") val finalScores: Map<String, Int> = emptyMap()
)

/** Joueur persisté (pour amis / classement global depuis la BDD). */
data class PlayerProfile(
    @SerializedName("client_id") val clientId: String,
    @SerializedName("display_name") val displayName: String? = null,
    @SerializedName("last_seen_at") val lastSeenAt: Long? = null,
    @SerializedName("last_score") val lastScore: Int = 0
)
