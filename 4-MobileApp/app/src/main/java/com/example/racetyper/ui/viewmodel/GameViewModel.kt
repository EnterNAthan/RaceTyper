package com.example.racetyper.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.racetyper.data.SettingsManager
import com.example.racetyper.data.model.Friend
import com.example.racetyper.data.model.GameState
import com.example.racetyper.data.model.Player
import com.example.racetyper.data.model.RoundClassement
import com.example.racetyper.data.repository.GameRepository
import com.example.racetyper.data.websocket.ConnectionState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class GameViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = GameRepository()
    private val settingsManager = SettingsManager(application)

    val connectionState: StateFlow<ConnectionState> = repository.connectionState
    val gameState: StateFlow<GameState> = repository.gameState
    val scores: StateFlow<Map<String, Int>> = repository.scores
    val lastRoundClassement: StateFlow<RoundClassement?> = repository.lastRoundClassement

    val serverUrl: StateFlow<String> = settingsManager.serverUrl
        .stateIn(viewModelScope, SharingStarted.Eagerly, SettingsManager.DEFAULT_SERVER_URL)

    private val _friends = MutableStateFlow<List<Friend>>(emptyList())
    val friends: StateFlow<List<Friend>> = _friends.asStateFlow()

    init {
        _friends.value = repository.getMockFriends()
    }

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

    fun getPlayersSortedByScore(): List<Player> {
        return gameState.value.players.values
            .sortedByDescending { it.score }
    }

    fun getRankingList(): List<Pair<Int, Player>> {
        return getPlayersSortedByScore()
            .mapIndexed { index, player -> (index + 1) to player }
    }

    override fun onCleared() {
        super.onCleared()
        repository.disconnect()
    }
}
