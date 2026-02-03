package com.example.racetyper.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class SettingsManager(private val context: Context) {

    companion object {
        private val SERVER_URL_KEY = stringPreferencesKey("server_url")
        const val DEFAULT_SERVER_URL = "192.168.1.100:8000"
    }

    val serverUrl: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[SERVER_URL_KEY] ?: DEFAULT_SERVER_URL
    }

    suspend fun setServerUrl(url: String) {
        context.dataStore.edit { preferences ->
            preferences[SERVER_URL_KEY] = url
        }
    }
}
