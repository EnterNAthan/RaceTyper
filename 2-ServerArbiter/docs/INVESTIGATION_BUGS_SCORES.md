# Investigation: Scores ne s'actualisent pas à la fin de la manche

## Résumé du problème
Les scores affichés à l'arbitre et/ou aux joueurs ne s'actualisent plus après la fin d'une manche. Les points sont calculés mais ne semblent pas être transmis correctement.

---

## 🐛 Bugs Identifiés

### 1. **BUG CRITIQUE: Message d'actualisation des scores manquant**
**Localisation:** `GameManager.py`, ligne 659-664 dans `process_round_end()`

**Problème:**
```python
# 4. Envoyer le classement de la manche ET les scores globaux à tout le monde
await self.broadcast({
    "type": "round_classement", 
    "classement": classement_data,
    "global_scores": self.scores
})
```

✅ **Le message est envoyé**, mais il faut vérifier que le client l'écoute correctement.

**Potential Issue:** Le message type `"round_classement"` doit être géré côté client (app mobile). Si le client ignore ce message, les scores ne seront jamais affichés.

---

### 2. **BUG POTENTIEL: Scores n'incluent que les bonus/malus déclarés**
**Localisation:** `GameManager.py`, ligne 637-646 dans `process_round_end()`

**Problème:**
```python
for i, (client_id, data) in enumerate(sorted_results):
    rank = i + 1
    
    # Attribuer des points en fonction du classement
    points_de_classement = max(0, 1000 - (rank * 200))
    self.scores[client_id] += points_de_classement  # ✅ Score mise à jour
    
    # Gérer les bonus/malus de la phrase
    triggered_objects = data.get("objects_triggered", [])
    await self.apply_effects(client_id, triggered_objects)
```

✅ **Les points de classement SONT ajoutés** au score dans `self.scores[client_id]`

✅ **Les bonus/malus SONT appliqués** via `apply_effects()`

---

### 3. **BUG: Message de fin de manche peut être perdu si la BD échoue**
**Localisation:** `GameManager.py`, ligne 657 dans `process_round_end()`

**Problème:**
```python
# 3. Persister les résultats de la manche en BDD
await self._save_round_results(self.current_phrase_index)  # ❌ Pas de gestion d'erreur

# 4. Envoyer le classement...
await self.broadcast({
    "type": "round_classement", 
    "classement": classement_data,
    "global_scores": self.scores
})
```

**Impact:** Si `_save_round_results()` échoue ET lève une exception non attrapée, le `broadcast()` n'aura jamais lieu.

**Solution:** Ajouter try/except autour de `_save_round_results()` pour que ça n'empêche pas la diffusion.

---

### 4. **BUG POSSIBLE: Race condition entre joueurs et bot**
**Localisation:** `GameManager.py`, ligne 613-619 dans `process_message()`

**Problème:**
```python
# 3. VÉRIFIER SI LA MANCHE EST TERMINÉE
expected_results = len(self.active_players) + (1 if self.bot_active else 0)
if len(self.current_round_results) >= expected_results:
    # OUI ! Tout le monde a fini.
    await self.process_round_end()
```

**Issue:** Si le bot envoie son résultat juste avant le dernier joueur humain, la manche peut être traitée deux fois par deux coroutines asynchrones simultanées. Cela pourrait causer:
- Les scores être doublés
- Les messages `round_classement` être envoyés deux fois
- Des calculs de classement conflictuels

**Solution:** Ajouter un verrou (lock) ou un flag pour éviter que `process_round_end()` soit appelée deux fois.

---

### 5. **BUG: Attente de 5 secondes bloque les autres joueurs**
**Localisation:** `GameManager.py`, ligne 667 dans `process_round_end()`

**Problème:**
```python
# Attendre 5 secondes pour que les joueurs voient le classement
await asyncio.sleep(5) 
```

**Issue:** Cette pause de 5 secondes est **BLOQUANTE** pour tous les joueurs. Si un joueur essaie d'envoyer un message pendant ce temps, il ne sera pas traité.

**Symptôme:** Les clients peuvent sembler "gelés" pendant 5 secondes.

**Solution:** Utiliser un mécanisme de timeout côté client plutôt qu'une sleep côté serveur.

---

### 6. **BUG: Les scores du bot ne sont pas persister en BDD**
**Localisation:** `GameManager.py`, ligne 245-247 dans `_save_round_results()`

**Problème:**
```python
for rank, (client_id, data) in enumerate(sorted_results, start=1):
    player_id = await self._get_or_create_player_id(client_id)
    if player_id is None:
        continue  # ❌ Le bot est skippé car client_id == self.bot_id
```

**Impact:** Les résultats du bot ne sont jamais sauvegardés en BDD car `_get_or_create_player_id(self.bot_id)` retourne `None`. Cela n'affecte pas l'affichage en temps réel, mais les stats historiques du bot seront manquantes.

---

### 7. **BUG: Exception possible dans `apply_effects()` non gérée**
**Localisation:** `GameManager.py`, ligne 702-727 dans `apply_effects()`

**Problème:**
```python
async def apply_effects(self, client_id: str, objects: list) -> None:
    for obj in objects:
        if obj.get("type") == "bonus" and obj.get("success"):
            bonus_points = self.object_manager.get_bonus_effect()
            self.scores[client_id] += bonus_points  # ❌ Peut lever KeyError si client_id absent
```

**Issue:** Si `client_id` n'existe plus dans `self.scores` (déconnecté juste avant), une `KeyError` lève une exception qui arrête le traitement de la manche.

**Solution:** Ajouter une vérification `if client_id in self.scores` ou un try/except.

---

### 8. **BUG: Scores pas actualisés pour les joueurs déjà connectés qui regardent**
**Localisation:** Pas de `player_update` après `process_round_end()`

**Problème:** Après `process_round_end()`, on envoie `round_classement` avec les nouveaux scores globaux, **mais** les joueurs qui regardent l'interface ne reçoivent pas un message `player_update` explicite.

**Issue:** Certaines interfaces client attendent un message `"type": "player_update"` pour actualiser l'affichage des scores.

**Solution:** Ajouter un broadcast `player_update` avec les nouveaux scores après `process_round_end()`.

---

### 9. **BUG: Si la BD n'est pas disponible, `_save_round_results()` peut crash silencieusement**
**Localisation:** `GameManager.py`, ligne 230-261 dans `_save_round_results()` et `_save_round_results_sync()`

**Problème:**
```python
async def _save_round_results(self, round_index: int) -> None:
    if self._sync_engine:
        await asyncio.to_thread(self._save_round_results_sync, round_index)
        return
    if not self._session_maker or self.current_game_id is None:
        return  # ✅ Fallback OK
    try:
        # ...
    except Exception as e:
        log_server(f"_save_round_results: {e}", "WARNING")  # ✅ Exception loggée
```

✅ **Bien géré** — pas de crash, juste un log.

---

## 📊 Ordre de priorité des fixes

1. **CRITIQUE:** Bug #4 (Race condition) — Peut causer des scores doublés
2. **HAUTE:** Bug #3 (BD timeout) — Empêche la diffusion des scores
3. **HAUTE:** Bug #8 (`player_update` manquant) — Interface n'actualise pas l'affichage
4. **MOYENNE:** Bug #7 (KeyError dans `apply_effects()`)
5. **MOYENNE:** Bug #5 (5 secondes de sleep bloquant)
6. **BASSE:** Bug #6 (Bot pas en BDD) — Affichage en temps réel OK, stats historiques manquantes

---

## ✅ Ce qui fonctionne correctement

- ✅ Scores sont correctement calculés en mémoire
- ✅ Points de classement sont correctement attribués
- ✅ Bonus/malus sont appliqués
- ✅ Message `round_classement` est envoyé à tous les joueurs
- ✅ Si la BD n'est pas dispo, le jeu continue sans crash
- ✅ Reset des scores à la fin de la partie

---

## 🔍 Diagnostic recommandé

Pour identifier le problème exact, vérifiez:

1. **Côté serveur:** Activez les logs avec niveau `DEBUG` et vérifiez qu'on voit:
   - `"Fin de la manche ! Calcul du classement..."`
   - `"Lancement de la manche N"`
   - Pas d'erreur dans les logs

2. **Côté client (app mobile):** Vérifiez que le client écoute:
   - Le message `"type": "round_classement"` et actualise l'affichage
   - Le message `"type": "player_update"` et actualise les scores
   - Le message `"type": "new_phrase"` pour passer à la manche suivante

3. **Avec la BD indisponible:** Assurez-vous que le serveur continue à tourner sans crash (c'est OK que la BD soit manquante).

---

## 🛠️ Fixes proposés (détails dans les fichiers suivants)

Voir `GameManager_FIXES.py` pour les corrections proposées.
