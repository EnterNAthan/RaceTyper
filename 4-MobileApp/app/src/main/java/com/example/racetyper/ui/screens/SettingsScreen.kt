package com.example.racetyper.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.racetyper.data.websocket.ConnectionState
import com.example.racetyper.ui.components.ConnectionStatus
import com.example.racetyper.ui.viewmodel.GameViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: GameViewModel,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val connectionState by viewModel.connectionState.collectAsState()
    val currentServerUrl by viewModel.serverUrl.collectAsState()
    var serverUrlInput by remember(currentServerUrl) { mutableStateOf(currentServerUrl) }
    var showSaved by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Parametres") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Retour"
                        )
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Server Configuration Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Text(
                        text = "Configuration serveur",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )

                    OutlinedTextField(
                        value = serverUrlInput,
                        onValueChange = {
                            serverUrlInput = it
                            showSaved = false
                        },
                        label = { Text("Adresse du serveur") },
                        placeholder = { Text("192.168.1.100:8000") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = {
                                viewModel.updateServerUrl(serverUrlInput)
                                showSaved = true
                            },
                            modifier = Modifier.weight(1f)
                        ) {
                            if (showSaved) {
                                Icon(Icons.Default.Check, contentDescription = null)
                                Text("  Sauvegarde")
                            } else {
                                Text("Sauvegarder")
                            }
                        }

                        Button(
                            onClick = {
                                viewModel.connectTo(serverUrlInput)
                            },
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = null)
                            Text("  Connecter")
                        }
                    }
                }
            }

            // Connection Status Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = "Etat de la connexion",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )

                    HorizontalDivider()

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Statut:",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        ConnectionStatus(connectionState = connectionState)
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Serveur actuel:",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Text(
                            text = currentServerUrl,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    if (connectionState is ConnectionState.Error) {
                        Text(
                            text = "Erreur: ${(connectionState as ConnectionState.Error).message}",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.Red
                        )
                    }

                    if (connectionState is ConnectionState.Connected) {
                        OutlinedButton(
                            onClick = { viewModel.disconnect() },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Deconnecter")
                        }
                    }
                }
            }

            // Info Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "A propos",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "RaceTyper Mobile v1.0",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Text(
                        text = "Application spectateur pour le jeu de course de frappe distribue RaceTyper.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
