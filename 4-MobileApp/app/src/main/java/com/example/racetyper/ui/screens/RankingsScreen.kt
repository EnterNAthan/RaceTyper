package com.example.racetyper.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.racetyper.ui.components.GameBackground // Assure-toi d'avoir cet import
import com.example.racetyper.ui.components.ModernGameCard
import com.example.racetyper.ui.components.PlayerCard
import com.example.racetyper.ui.viewmodel.GameViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RankingsScreen(
    viewModel: GameViewModel,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val gameState by viewModel.gameState.collectAsState()
    val sortedPlayers = gameState.players.values.sortedByDescending { it.score }

    // 1. On enveloppe tout dans le fond lumineux
    GameBackground(modifier = modifier) {
        Scaffold(
            // 2. IMPORTANT : On rend le Scaffold transparent pour voir le fond
            containerColor = Color.Transparent,
            topBar = {
                TopAppBar(
                    title = { Text("Classement Global") },
                    navigationIcon = {
                        IconButton(onClick = onNavigateBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, "Retour")
                        }
                    },
                    // 3. On rend la barre transparente aussi
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = Color.Transparent,
                        titleContentColor = Color.White,
                        navigationIconContentColor = Color.White
                    )
                )
            }
        ) { padding ->
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Header du classement
                item {
                    ModernGameCard(title = "Podium", icon = Icons.Default.EmojiEvents) {
                        if (sortedPlayers.isEmpty()) {
                            Text("Aucun joueur connecté", color = Color.Gray)
                        } else {
                            Text("${sortedPlayers.size} pilotes en lice", color = Color.LightGray)
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }

                itemsIndexed(sortedPlayers) { index, player ->
                    PlayerCard(
                        player = player,
                        rank = index + 1
                    )
                }
            }
        }
    }
}