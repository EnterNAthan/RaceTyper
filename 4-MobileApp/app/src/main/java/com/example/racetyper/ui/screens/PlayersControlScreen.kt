package com.example.racetyper.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.Gif
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.racetyper.data.model.MalusType
import com.example.racetyper.data.model.Player
import com.example.racetyper.ui.components.GameBackground
import com.example.racetyper.ui.viewmodel.GameViewModel
import com.example.racetyper.ui.viewmodel.MalusSendResult
import com.example.racetyper.data.websocket.ConnectionState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlayersControlScreen(
    viewModel: GameViewModel,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val gameState by viewModel.gameState.collectAsState()
    val connectionState by viewModel.connectionState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    // Filtrer les joueurs actifs (pas les spectateurs / bot)
    val activePlayers = remember(gameState) {
        viewModel.getActivePlayersForControl()
    }

    val isConnected = connectionState is ConnectionState.Connected

    // Feedback de l'envoi de malus via Snackbar
    LaunchedEffect(Unit) {
        viewModel.malusEvents.collect { result ->
            when (result) {
                is MalusSendResult.Success -> {
                    snackbarHostState.showSnackbar(
                        "${result.malusType.label} envoyé à ${result.targetId}"
                    )
                }
                is MalusSendResult.Failure -> {
                    snackbarHostState.showSnackbar("Erreur : ${result.reason}")
                }
            }
        }
    }

    GameBackground(modifier = modifier) {
        Scaffold(
            containerColor = Color.Transparent,
            snackbarHost = { SnackbarHost(snackbarHostState) },
            topBar = {
                TopAppBar(
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Default.SportsEsports,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(24.dp)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text("Contrôle Joueurs")
                        }
                    },
                    navigationIcon = {
                        IconButton(onClick = onNavigateBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, "Retour")
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color.Transparent,
                        titleContentColor = Color.White,
                        navigationIconContentColor = Color.White
                    )
                )
            }
        ) { paddingValues ->

            if (!isConnected) {
                // État déconnecté
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            Icons.Default.WifiOff,
                            contentDescription = null,
                            tint = Color.Gray,
                            modifier = Modifier.size(64.dp)
                        )
                        Spacer(Modifier.height(16.dp))
                        Text(
                            "Non connecté au serveur",
                            color = Color.Gray,
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(
                            "Connectez-vous depuis les paramètres",
                            color = Color.Gray.copy(alpha = 0.6f),
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            } else if (activePlayers.isEmpty()) {
                // Aucun joueur actif
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            Icons.Default.SportsEsports,
                            contentDescription = null,
                            tint = Color.Gray,
                            modifier = Modifier.size(64.dp)
                        )
                        Spacer(Modifier.height(16.dp))
                        Text(
                            "Aucun joueur connecté",
                            color = Color.Gray,
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(
                            "Les joueurs apparaîtront ici quand ils se connecteront",
                            color = Color.Gray.copy(alpha = 0.6f),
                            style = MaterialTheme.typography.bodySmall,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(horizontal = 32.dp)
                        )
                    }
                }
            } else {
                // Liste des joueurs avec leurs boutons de malus
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    item {
                        Text(
                            "GAME MASTER",
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary,
                            letterSpacing = 3.sp,
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                        Text(
                            "${activePlayers.size} joueur(s) en course",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White.copy(alpha = 0.5f)
                        )
                        Spacer(Modifier.height(8.dp))
                    }

                    items(activePlayers, key = { it.clientId }) { player ->
                        PlayerMalusCard(
                            player = player,
                            onSendMalus = { malusType ->
                                viewModel.sendMalus(player.clientId, malusType)
                            }
                        )
                    }
                }
            }
        }
    }
}

// ─────────────────────────── Player Card with Malus Buttons ───────────────────

@Composable
private fun PlayerMalusCard(
    player: Player,
    onSendMalus: (MalusType) -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = Color(0xFF1E1E2C).copy(alpha = 0.7f)
        ),
        border = BorderStroke(
            1.dp,
            Brush.linearGradient(
                colors = listOf(
                    Color.White.copy(alpha = 0.12f),
                    Color.White.copy(alpha = 0.04f)
                )
            )
        )
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            // En-tête du joueur
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = player.clientId,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text(
                        text = "${player.score} pts",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // Boutons de malus
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                MalusButton(
                    label = "GIF",
                    icon = Icons.Default.Gif,
                    color = Color(0xFFE040FB),
                    onClick = { onSendMalus(MalusType.INTRUSIVE_GIF) },
                    modifier = Modifier.weight(1f)
                )
                MalusButton(
                    label = "Clavier",
                    icon = Icons.Default.Block,
                    color = Color(0xFFFF5252),
                    onClick = { onSendMalus(MalusType.DISABLE_KEYBOARD) },
                    modifier = Modifier.weight(1f)
                )
                MalusButton(
                    label = "Sirène",
                    icon = Icons.Default.NotificationsActive,
                    color = Color(0xFFFFAB40),
                    onClick = { onSendMalus(MalusType.PHYSICAL_DISTRACTION) },
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

// ─────────────────────────── Malus Button ─────────────────────────────────────

@Composable
private fun MalusButton(
    label: String,
    icon: ImageVector,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        modifier = modifier.height(56.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = color.copy(alpha = 0.15f),
            contentColor = color
        ),
        border = BorderStroke(1.dp, color.copy(alpha = 0.3f)),
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                modifier = Modifier.size(20.dp)
            )
            Text(
                text = label,
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1
            )
        }
    }
}
