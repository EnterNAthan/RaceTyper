package com.example.racetyper.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.racetyper.data.model.Player

@Composable
fun ScoreBoard(
    players: List<Player>,
    title: String = "Classement",
    showTitle: Boolean = true,
    maxDisplay: Int = 5,
    modifier: Modifier = Modifier
) {
    val sortedPlayers = players.sortedByDescending { it.score }.take(maxDisplay)

    Column(modifier = modifier.fillMaxWidth()) {
        if (showTitle) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                modifier = Modifier.padding(bottom = 8.dp)
            )
        }

        if (sortedPlayers.isEmpty()) {
            Text(
                text = "Aucun joueur connecté",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Gray,
                modifier = Modifier.padding(vertical = 8.dp)
            )
        } else {
            sortedPlayers.forEachIndexed { index, player ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "${index + 1}.",
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Bold,
                            color = if (index < 3) MaterialTheme.colorScheme.primary else Color.Gray,
                            modifier = Modifier.width(24.dp)
                        )
                        Text(
                            text = player.clientId,
                            style = MaterialTheme.typography.bodyLarge,
                            color = Color.White
                        )
                    }
                    Text(
                        text = "${player.score} pts",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold
                    )
                }
                if (index < sortedPlayers.size - 1) {
                    HorizontalDivider(color = Color.White.copy(alpha = 0.05f))
                }
            }
        }
    }
}