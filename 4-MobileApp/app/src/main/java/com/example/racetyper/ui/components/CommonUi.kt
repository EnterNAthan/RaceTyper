package com.example.racetyper.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// --- LE FOND QUI CHANGE TOUT ---
@Composable
fun GameBackground(
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0A0A10)) // Fond noir bleuté profond
    ) {
        // On dessine des lumières d'ambiance
        Canvas(modifier = Modifier.fillMaxSize()) {
            val width = size.width
            val height = size.height

            // 1. Orbe VIOLET (Haut Gauche)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color(0xFF6200EE).copy(alpha = 0.2f), Color.Transparent),
                    center = Offset(0f, 0f),
                    radius = width * 1.2f
                )
            )

            // 2. Orbe CYAN/BLEU (Bas Droite)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color(0xFF03DAC6).copy(alpha = 0.15f), Color.Transparent),
                    center = Offset(width, height),
                    radius = width * 1.0f
                )
            )

            // 3. Orbe CENTRAL (Subtil)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(Color(0xFF3700B3).copy(alpha = 0.1f), Color.Transparent),
                    center = Offset(width / 2, height / 2),
                    radius = width * 0.8f
                )
            )
        }

        // Le contenu de l'écran par dessus
        content()
    }
}

// --- LA CARTE "VERRE FUMÉ" ---
@Composable
fun ModernGameCard(
    title: String? = null,
    icon: ImageVector? = null,
    accentColor: Color = MaterialTheme.colorScheme.primary,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(
            // C'est ici que la magie opère : une couleur semi-transparente
            containerColor = Color(0xFF1E1E2C).copy(alpha = 0.6f)
        ),
        // Une bordure très fine pour capter la lumière
        border = BorderStroke(1.dp, Brush.linearGradient(
            colors = listOf(
                Color.White.copy(alpha = 0.15f),
                Color.White.copy(alpha = 0.05f)
            )
        ))
    ) {
        Column(modifier = Modifier.padding(24.dp)) {
            if (title != null) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(bottom = 16.dp)
                ) {
                    if (icon != null) {
                        Icon(
                            imageVector = icon,
                            contentDescription = null,
                            tint = accentColor,
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                    }
                    Text(
                        text = title.uppercase(),
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = Color.White.copy(alpha = 0.7f),
                        letterSpacing = 1.5.sp
                    )
                }
            }
            content()
        }
    }
}