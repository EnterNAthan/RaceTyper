package com.example.racetyper.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.racetyper.data.model.GameStatus
import com.example.racetyper.data.websocket.ConnectionState
import com.example.racetyper.ui.components.GameBackground
import com.example.racetyper.ui.components.ModernGameCard
import com.example.racetyper.ui.components.ScoreBoard
import com.example.racetyper.ui.viewmodel.GameViewModel

@Composable
fun HomeScreen(
    viewModel: GameViewModel,
    onNavigateToRankings: () -> Unit,
    modifier: Modifier = Modifier
) {
    val connectionState by viewModel.connectionState.collectAsState()
    val gameState by viewModel.gameState.collectAsState()
    val serverUrl by viewModel.serverUrl.collectAsState()

    GameBackground(modifier = modifier) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp)
                .padding(top = 16.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "RaceTyper",
                        style = MaterialTheme.typography.displaySmall,
                        fontWeight = FontWeight.Black,
                        color = Color.White
                    )
                    Text(
                        text = "Ready to race?",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                ConnectionBadge(connectionState)
            }

            ModernGameCard(
                title = "Live Status",
                icon = Icons.Default.Bolt,
                accentColor = if (gameState.status == GameStatus.PLAYING) Color(0xFF00E676) else MaterialTheme.colorScheme.primary
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text(
                        text = when (gameState.status) {
                            GameStatus.WAITING -> "EN ATTENTE"
                            GameStatus.PLAYING -> "COURSE EN COURS"
                            GameStatus.PAUSED -> "PAUSE"
                            GameStatus.FINISHED -> "TERMINÉ"
                            GameStatus.GAME_OVER -> "PARTIE TERMINÉE"
                        },
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )

                    if (gameState.currentPhrase.isNotEmpty()) {
                        Surface(
                            color = Color.Black.copy(alpha = 0.3f),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = gameState.currentPhrase.replace("^^", "").replace("&", ""),
                                style = MaterialTheme.typography.bodyLarge,
                                modifier = Modifier.padding(16.dp),
                                color = Color.LightGray,
                                fontFamily = MaterialTheme.typography.bodyLarge.fontFamily
                            )
                        }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        StatItem(label = "Joueurs", value = "${gameState.players.size}")
                        StatItem(label = "Manche", value = "${gameState.currentRound}/${gameState.totalRounds}")
                    }
                }
            }

            if (connectionState !is ConnectionState.Connected) {
                ModernGameCard(title = "Serveur", icon = Icons.Default.Refresh) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = serverUrl, color = Color.Gray)
                        Button(
                            onClick = { viewModel.connect() },
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                        ) {
                            Text("Connecter")
                        }
                    }
                }
            }

            ModernGameCard(title = "Leaderboard", icon = null) {
                ScoreBoard(
                    players = gameState.players.values.toList(),
                    showTitle = false,
                    maxDisplay = 3
                )
                Spacer(modifier = Modifier.height(16.dp))
                OutlinedButton(
                    onClick = onNavigateToRankings,
                    modifier = Modifier.fillMaxWidth(),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.5f)),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                ) {
                    Text("Voir tout le classement")
                }
            }
        }
    }
}

@Composable
fun StatItem(label: String, value: String) {
    Column {
        Text(text = value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = Color.White)
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = Color.Gray)
    }
}

@Composable
fun ConnectionBadge(state: ConnectionState) {
    val color = when (state) {
        is ConnectionState.Connected -> Color(0xFF00E676)
        is ConnectionState.Connecting -> Color(0xFFFFC107)
        else -> Color(0xFFFF5252)
    }
    Surface(
        color = color.copy(alpha = 0.1f),
        shape = RoundedCornerShape(50),
        border = BorderStroke(1.dp, color.copy(alpha = 0.3f))
    ) {
        Row(modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(6.dp).background(color, CircleShape))
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = if (state is ConnectionState.Connected) "LIVE" else "OFF",
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                color = color
            )
        }
    }
}
