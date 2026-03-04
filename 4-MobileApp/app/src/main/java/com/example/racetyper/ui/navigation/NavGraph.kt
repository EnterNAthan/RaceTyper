package com.example.racetyper.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.example.racetyper.ui.screens.HomeScreen
import com.example.racetyper.ui.screens.PlayersControlScreen
import com.example.racetyper.ui.screens.RankingsScreen
import com.example.racetyper.ui.screens.SettingsScreen
import com.example.racetyper.ui.viewmodel.GameViewModel

sealed class Screen(val route: String) {
    object Home : Screen("home")
    object Rankings : Screen("rankings")
    object PlayersControl : Screen("players_control")
    object Settings : Screen("settings")
}

@Composable
fun NavGraph(
    navController: NavHostController,
    viewModel: GameViewModel,
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = Screen.Home.route,
        modifier = modifier
    ) {
        composable(Screen.Home.route) {
            HomeScreen(
                viewModel = viewModel,
                onNavigateToRankings = {
                    navController.navigate(Screen.Rankings.route)
                }
            )
        }

        composable(Screen.Rankings.route) {
            RankingsScreen(
                viewModel = viewModel,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }

        composable(Screen.PlayersControl.route) {
            PlayersControlScreen(
                viewModel = viewModel,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }

        composable(Screen.Settings.route) {
            SettingsScreen(
                viewModel = viewModel,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
