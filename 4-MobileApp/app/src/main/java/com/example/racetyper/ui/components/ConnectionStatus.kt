package com.example.racetyper.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.racetyper.data.websocket.ConnectionState

@Composable
fun ConnectionStatus(
    connectionState: ConnectionState,
    modifier: Modifier = Modifier
) {
    val (color, text) = when (connectionState) {
        is ConnectionState.Connected -> Color(0xFF4CAF50) to "Connecté"
        is ConnectionState.Connecting -> Color(0xFFFFC107) to "Connexion..."
        is ConnectionState.Reconnecting -> Color(0xFFFF9800) to "Reconnexion #${connectionState.attempt}..."
        is ConnectionState.Disconnected -> Color(0xFF9E9E9E) to "Déconnecté"
        is ConnectionState.Error -> Color(0xFFF44336) to "Erreur"
    }

    val animatedColor by animateColorAsState(targetValue = color, label = "statusColor")

    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        color = animatedColor.copy(alpha = 0.15f)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(animatedColor, CircleShape)
            )
            Text(
                text = text,
                style = MaterialTheme.typography.labelMedium,
                color = animatedColor
            )
        }
    }
}
