package com.example.racetyper.ui.components

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.racetyper.data.model.Player

@Composable
fun PlayerCard(
    player: Player,
    rank: Int,
    modifier: Modifier = Modifier
) {
    val rankColor = when (rank) {
        1 -> Color(0xFFFFD700) // Or
        2 -> Color(0xFFC0C0C0) // Argent
        3 -> Color(0xFFCD7F32) // Bronze
        else -> Color.Gray       // Gris pour les autres
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize(),
        shape = RoundedCornerShape(16.dp), // Arrondi un peu plus moderne
        colors = CardDefaults.cardColors(
            // Fond sombre semi-transparent (Glassmorphism) pour aller avec le fond néon
            containerColor = Color(0xFF252538).copy(alpha = 0.6f)
        ),
        // Petite bordure lumineuse pour le Top 3, sinon transparente
        border = BorderStroke(1.dp, if (rank <= 3) rankColor.copy(alpha = 0.5f) else Color.White.copy(alpha = 0.05f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp) // On gère la profondeur avec la couleur, pas l'ombre
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Rank badge
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        // Fond du badge légèrement transparent
                        .background(if (rank <= 3) rankColor.copy(alpha = 0.2f) else Color.White.copy(alpha = 0.1f)),
                    contentAlignment = Alignment.Center
                ) {
                    if (rank <= 3) {
                        Icon(
                            imageVector = Icons.Default.EmojiEvents,
                            contentDescription = "Rank $rank",
                            tint = rankColor, // L'icone prend la couleur vive
                            modifier = Modifier.size(24.dp)
                        )
                    } else {
                        Text(
                            text = "#$rank",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color.White // Texte blanc pour lisibilité
                        )
                    }
                }

                // Player info
                Column {
                    Text(
                        text = player.clientId,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.White // Nom en blanc
                    )
                    if (player.isConnected) {
                        Text(
                            text = "En ligne",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF00E676) // Vert néon
                        )
                    }
                }
            }

            // Score
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${player.score}",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Black, // Très gras pour le score
                    color = MaterialTheme.colorScheme.primary // Violet (Ta couleur préférée)
                )
                Text(
                    text = "points",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray
                )
            }
        }
    }
}

@Composable
fun PlayerCardCompact(
    player: Player,
    rank: Int,
    modifier: Modifier = Modifier
) {
    val rankColor = when (rank) {
        1 -> Color(0xFFFFD700)
        2 -> Color(0xFFC0C0C0)
        3 -> Color(0xFFCD7F32)
        else -> Color.Gray
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(CircleShape)
                    .background(if (rank <= 3) rankColor else Color.White.copy(alpha = 0.1f)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "$rank",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    // Si c'est le top 3 (fond coloré) texte noir/foncé, sinon blanc
                    color = if (rank <= 3) Color.Black else Color.White
                )
            }
            Text(
                text = player.clientId,
                style = MaterialTheme.typography.bodyLarge,
                color = Color.White // Nom en blanc pour le scoreboard
            )
        }
        Text(
            text = "${player.score} pts",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary // Violet
        )
    }
}