package com.example.racetyper.data.model

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

data class RoundResult(
    val rank: Int,
    val clientId: String,
    val time: Double,
    val scoreAdded: Int
)

data class RoundClassement(
    val classement: List<RoundResult>,
    val globalScores: Map<String, Int>
)

data class Friend(
    val id: String,
    val name: String,
    val avatarUrl: String? = null,
    val isOnline: Boolean = false,
    val lastScore: Int = 0
)
