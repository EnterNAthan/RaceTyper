# Fixes Proposées pour les Bugs de Scores

## Fix #1: Ajouter un verrou pour éviter les race conditions

**Problème:** `process_round_end()` peut être appelée deux fois simultanément

**Localisation:** `GameManager.py`, dans la classe `GameManager.__init__()`

**Code à ajouter:**
```python
def __init__(self) -> None:
    # ... code existant ...
    self._round_processing_lock = asyncio.Lock()  # ✅ Ajouter cette ligne
```

**Code à modifier dans `process_round_end()`:**
```python
async def process_round_end(self) -> None:
    """Clôture une manche avec verrou pour éviter les race conditions."""
    async with self._round_processing_lock:  # ✅ Ajouter cette ligne
        log_server("Fin de la manche ! Calcul du classement...")
        # ... reste du code ...
```

---

## Fix #2: Protéger l'appel à `_save_round_results()` avec try/except

**Problème:** Si la BD échoue, le broadcast des scores n'a pas lieu

**Localisation:** `GameManager.py`, dans `process_round_end()` ligne 657

**Code à modifier:**
```python
# AVANT:
await self._save_round_results(self.current_phrase_index)

# APRÈS:
try:
    await self._save_round_results(self.current_phrase_index)
except Exception as e:
    log_server(f"Erreur lors de la sauvegarde des résultats: {e}", "WARNING")
    # Continue malgré tout pour que les scores soient diffusés
```

---

## Fix #3: Ajouter un message `player_update` après le classement

**Problème:** L'interface client ne sait pas que les scores ont changé

**Localisation:** `GameManager.py`, dans `process_round_end()` après le broadcast du classement

**Code à ajouter (après ligne 664):**
```python
# 4a. Envoyer le classement de la manche ET les scores globaux
await self.broadcast({
    "type": "round_classement", 
    "classement": classement_data,
    "global_scores": self.scores
})

# ✅ AJOUTER CETTE LIGNE POUR FORCER LA MISE À JOUR DE L'INTERFACE:
await self.broadcast({"type": "player_update", "scores": self.scores})
```

---

## Fix #4: Vérifier que le client existe avant d'appliquer les effets

**Problème:** `apply_effects()` crash si le joueur s'est déconnecté

**Localisation:** `GameManager.py`, dans `apply_effects()` ligne 713 et 723

**Code à modifier:**
```python
# AVANT (ligne 713):
self.scores[client_id] += bonus_points

# APRÈS:
if client_id in self.scores:
    self.scores[client_id] += bonus_points
else:
    log_server(f"Joueur {client_id} bonus non appliqué (joueur déconnecté)", "WARNING")

# MÊME CHOSE POUR LE MALUS:
# AVANT (ligne 723):
await self.send_to_client(target_player, {...})

# APRÈS:
if target_player in self.active_players:  # Vérifier que le joueur existe toujours
    await self.send_to_client(target_player, {...})
```

---

## Fix #5: Remplacer la pause bloquante par un signal côté client

**Problème:** `await asyncio.sleep(5)` bloque tous les autres joueurs

**Localisation:** `GameManager.py`, ligne 667 dans `process_round_end()`

**OPTION A - Garder la pause mais moins longue:**
```python
# AVANT:
await asyncio.sleep(5)

# APRÈS:
await asyncio.sleep(3)  # Réduire à 3 secondes au lieu de 5
```

**OPTION B - Meilleure approche (client-side timeout):**
```python
# Remplacer la pause par:
# Ne plus attendre côté serveur, laisser le client gérer l'affichage avec un timeout
# Le client lancera lui-même la requête pour la prochaine phrase
# Mais garder une sécurité anti-spam côté serveur (5 sec de délai minimum entre manches)
```

Pour OPTION B, il faudrait modifier le protocole pour que le client demande la phrase suivante, plutôt que le serveur la impose.

**Recommandation:** Pour l'instant, utiliser OPTION A (réduire à 3 secondes).

---

## Fix #6: Gérer correctement le changement de manche

**Problème:** Si les joueurs envoient des messages pendant la pause, ils sont traités par la nouvelle phrase

**Localisation:** `GameManager.py`, ligne 689 dans `process_round_end()`

**Code à améliorer:**
```python
# Vider les résultats pour la nouvelle manche
self.current_round_results = {}

# ✅ Vérifier aussi que game_status est toujours "playing"
if self.game_status != "playing":
    return  # Jeu a été arrêté entre-temps

new_phrase = self.phrases[self.current_phrase_index]
await self.broadcast({"type": "new_phrase", "phrase": new_phrase, "round_number": self.current_phrase_index})
```

---

## 🎯 Résumé des fixes par ordre d'importance

| Priority | Bug | Fix | Effort |
|----------|-----|-----|--------|
| 1 | Race condition (2x process_round_end) | Ajouter Lock asyncio | 5 min |
| 2 | BD fail = pas de broadcast scores | Try/except + log | 5 min |
| 3 | Interface ne sait pas actualiser | Ajouter player_update | 2 min |
| 4 | apply_effects() crash | Vérifier client_id existe | 3 min |
| 5 | Pause bloquante | Réduire à 3 sec ou refactoriser | 5-20 min |
| 6 | Changement de manche | Vérifier game_status | 2 min |

**Total temps de fix: ~20-30 minutes**

---

## 📝 Tests à faire après les fixes

1. **Test sans BD:**
   - Arrêter Docker/PostgreSQL
   - Lancer une partie
   - Vérifier que les scores s'actualisent correctement

2. **Test avec BD:**
   - Lancer Docker/PostgreSQL
   - Lancer une partie
   - Vérifier que les scores s'actualisent ET sont sauvegardés

3. **Test déconnexion rapide:**
   - Connecter 2 joueurs
   - 1er finit la phrase et se déconnecte immédiatement
   - 2e finit la phrase
   - Vérifier que les scores sont corrects et pas de crash

4. **Test race condition (bot + joueur):**
   - Activer le bot
   - Lancer une partie
   - Vérifier que chaque manche n'est traitée qu'une fois
   - Vérifier que les scores ne sont pas doublés

5. **Test interface admin:**
   - Vérifier que le tableau de bord admin se met à jour correctement
   - Vérifier que les scores s'affichent bien à la fin de chaque manche
