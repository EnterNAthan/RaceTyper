package com.example.racetyper.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.racetyper.data.model.Friend

@Composable
fun FriendCard(
    friend: Friend, // C'est ici que ça bloquait : il faut accepter 'friend'
    modifier: Modifier = Modifier
) {
    // Couleur du statut (Vert néon si en ligne, Gris si hors ligne)
    val statusColor = if (friend.isOnline) Color(0xFF00E676) else Color.Gray

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color(0xFF252538).copy(alpha = 0.6f)
        ),
        // Bordure verte si en ligne
        border = BorderStroke(1.dp, if (friend.isOnline) statusColor.copy(alpha = 0.3f) else Color.White.copy(alpha = 0.05f))
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
                // Avatar
                Box {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Person,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                    // Pastille de connexion
                    Box(
                        modifier = Modifier
                            .size(14.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF121212))
                            .padding(2.dp)
                            .align(Alignment.BottomEnd)
                    ) {
                        Box(
                            modifier = Modifier.fillMaxSize().clip(CircleShape).background(statusColor)
                        )
                    }
                }

                // Infos
                Column {
                    Text(
                        text = friend.name,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text(
                        text = if (friend.isOnline) "En ligne" else "Hors ligne",
                        style = MaterialTheme.typography.bodySmall,
                        color = statusColor
                    )
                }
            }

            // Score ami
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${friend.lastScore}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.White.copy(alpha = 0.9f)
                )
                Text(
                    text = "High Score",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray
                )
            }
        }
    }
}