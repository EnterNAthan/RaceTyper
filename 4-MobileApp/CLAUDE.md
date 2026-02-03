# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RaceTyper Mobile App - A companion Android application for the RaceTyper distributed typing race game. The app provides real-time visualization of scores, rankings, friend management (mock), and player status monitoring via WebSocket connection.

## Build Commands

```bash
# Build the project
./gradlew build

# Run unit tests
./gradlew test

# Run a specific test class
./gradlew test --tests "com.example.racetyper.ExampleUnitTest"

# Run instrumented tests (requires emulator/device)
./gradlew connectedAndroidTest

# Clean and rebuild
./gradlew clean build

# Install debug APK on connected device
./gradlew installDebug

# Generate release APK
./gradlew assembleRelease
```

## Tech Stack

- **Language**: Kotlin 2.0.21
- **UI**: Jetpack Compose with Material3
- **Async**: Coroutines + StateFlow
- **Network**: OkHttp WebSocket + Gson
- **Navigation**: Navigation Compose
- **State**: ViewModel + StateFlow
- **Storage**: DataStore Preferences
- **Min SDK**: 24 (Android 7.0)
- **Target/Compile SDK**: 36
- **Build System**: Gradle 8.11.1 with Kotlin DSL

## Architecture

### Package Structure
```
com.example.racetyper/
├── data/
│   ├── model/
│   │   └── Models.kt              # Player, GameState, RoundResult, Friend
│   ├── websocket/
│   │   └── RaceTyperWebSocket.kt  # OkHttp WebSocket client
│   ├── repository/
│   │   └── GameRepository.kt      # Single source of truth
│   └── SettingsManager.kt         # DataStore for server URL
├── ui/
│   ├── screens/
│   │   ├── HomeScreen.kt          # Dashboard with game status
│   │   ├── RankingsScreen.kt      # Full leaderboard
│   │   ├── FriendsScreen.kt       # Mock friends list
│   │   └── SettingsScreen.kt      # Server configuration
│   ├── components/
│   │   ├── ConnectionStatus.kt    # WebSocket status indicator
│   │   ├── PlayerCard.kt          # Player display component
│   │   └── ScoreBoard.kt          # Mini leaderboard
│   ├── viewmodel/
│   │   └── GameViewModel.kt       # Main ViewModel
│   ├── navigation/
│   │   └── NavGraph.kt            # Navigation setup
│   └── theme/                     # Material3 theme
└── MainActivity.kt                # Entry point with bottom nav
```

### Key Components
- **RaceTyperWebSocket**: Handles WebSocket connection and message parsing
- **GameRepository**: Exposes StateFlows for game state, scores, connection
- **GameViewModel**: AndroidViewModel managing UI state
- **NavGraph**: 4 screens with bottom navigation (Home, Rankings, Friends, Settings)

## Server Integration

Connects to RaceTyper Server at `../2-ServerArbiter/` via WebSocket.

### WebSocket Connection
- URL format: `ws://{serverUrl}/ws/{clientId}`
- Default client ID: `mobile-spectator`
- Server URL configurable in Settings screen

### WebSocket Message Types Handled
- `connection_accepted` - Connection confirmed
- `player_update` - Scores updated
- `new_phrase` - New round started
- `round_classement` - Round results
- `game_over` - Game finished
- `game_paused` - Game paused
- `game_reset` - Game reset
- `state_update` - Full game state

## Screens

1. **HomeScreen**: Game status, current phrase, top 3 players, connect/disconnect
2. **RankingsScreen**: Full leaderboard with last round results
3. **FriendsScreen**: Mock friends with online status (demo data)
4. **SettingsScreen**: Server URL config, connection test

## Configuration

Server URL stored in DataStore, default: `192.168.1.100:8000`

Permissions in AndroidManifest.xml:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

`android:usesCleartextTraffic="true"` enabled for local network testing.
