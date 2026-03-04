# Checklist de Test - Bugs de Scores Corrigés

## 🧪 Tests à Effectuer

### Test 1: Partie Complète SANS BD
**Objectif:** Vérifier que le jeu fonctionne sans persistance

**Étapes:**
1. [ ] Arrêter le conteneur Docker PostgreSQL
2. [ ] Lancer le serveur: `python .\run.py`
3. [ ] Attendre le message: `"BDD non disponible (mode sans persistance)"`
4. [ ] Connecter 2+ joueurs (via app mobile ou test client)
5. [ ] Lancer la partie depuis l'arbitre
6. [ ] Les joueurs tapent leurs phrases
7. [ ] À la fin de chaque manche, vérifier:
   - [ ] Les scores s'affichent correctement
   - [ ] Le classement est correct (rapide = meilleur)
   - [ ] Message `round_classement` + `player_update` dans les logs
   - [ ] Pas de crash côté serveur
8. [ ] Jouer 2-3 manches complètes
9. [ ] À la fin du jeu: vérifier `"type": "game_over"` envoyé

---

### Test 2: Partie Complète AVEC BD
**Objectif:** Vérifier que la persistance fonctionne

**Étapes:**
1. [ ] Lancer Docker: `docker-compose up -d` (depuis le dossier ServerArbiter)
2. [ ] Attendre que PostgreSQL soit prêt (~10 secondes)
3. [ ] Lancer le serveur: `python .\run.py`
4. [ ] Attendre le message: `"BDD PostgreSQL initialisée"`
5. [ ] Connecter 2+ joueurs
6. [ ] Lancer la partie depuis l'arbitre
7. [ ] Jouer 3-4 manches complètes
8. [ ] Vérifier dans les logs:
   - [ ] `"_save_round_results"` appelée sans erreur
   - [ ] Pas d'erreur PostgreSQL
9. [ ] À la fin du jeu: vérifier dans l'interface admin `/api/admin/export`
   - [ ] Les scores sont listés
   - [ ] Les résultats de manches sont sauvegardés
   - [ ] La partie apparaît dans `games_from_db`

---

### Test 3: Déconnexion Rapide d'un Joueur
**Objectif:** Vérifier pas de crash si déconnexion pendant manche

**Étapes:**
1. [ ] Connecter 2 joueurs: `pi-1` et `pi-2`
2. [ ] Lancer une manche
3. [ ] Attendre que `pi-1` finisse et envoie son résultat
4. [ ] IMMÉDIATEMENT déconnecter `pi-1` (fermer sa WebSocket)
5. [ ] `pi-2` finit sa phrase
6. [ ] Vérifier dans les logs du serveur:
   - [ ] Pas de `KeyError` ou `Traceback`
   - [ ] Message: `"Joueur pi-1 Déconnecté"`
   - [ ] Les scores de `pi-2` sont correctement calculés
7. [ ] Vérifier dans l'interface arbitre:
   - [ ] Le classement s'affiche correctement
   - [ ] Pas de "Unknown" ou valeurs bizarres

---

### Test 4: Race Condition (Bot + Joueur)
**Objectif:** Vérifier que la race condition est corrigée

**Étapes:**
1. [ ] Lancer le serveur
2. [ ] Depuis l'interface admin: Activer le bot IA (difficulté = "difficile")
3. [ ] Connecter 1 joueur: `pi-1`
4. [ ] Lancer la partie
5. [ ] Attendre que la manche 1 termine (le bot et le joueur finissent)
6. [ ] Vérifier dans les logs du serveur:
   - [ ] Exactement UN appel à `"Fin de la manche ! Calcul du classement..."`
   - [ ] Pas d'appel dupliqué au même traitement
7. [ ] Vérifier que les scores ne sont PAS doublés:
   - [ ] Points de classement = 1000 ou 800 (pas 1600, 1800, etc.)
8. [ ] Jouer 3 manches et vérifier la cohérence

**Vérification spécifique dans les logs:**
```
[DEBUG] Résultat de manche reçu de pi-1
[DEBUG] Résultat IA (difficile) pour la manche
[INFO] Fin de la manche ! Calcul du classement...
[INFO] Lancement de la manche 2
```

Les deux premiers logs peuvent être dans n'importe quel ordre, mais **le 3e ne doit apparaître qu'une seule fois**.

---

### Test 5: Bonus/Malus Sans Crash
**Objectif:** Vérifier que les effets ne causent pas de crash

**Étapes:**
1. [ ] Connecter 2 joueurs
2. [ ] Phrases avec bonus/malus (`^phrase^` ou `&malus&`)
3. [ ] Jouer une manche et déclencher des bonus/malus
4. [ ] Vérifier:
   - [ ] Les logs affichent: `"Joueur XX gagne YY points bonus!"`
   - [ ] Ou: `"Joueur XX envoie un malus 'ZZ' à XX!"`
   - [ ] Pas de `KeyError` ou crash
5. [ ] Scores augmentés par les bonus

---

### Test 6: Interface Admin Mise à Jour
**Objectif:** Vérifier que l'interface admin voit les scores s'actualiser

**Étapes:**
1. [ ] Ouvrir l'interface admin: `http://localhost:8000/`
2. [ ] Connecter des joueurs
3. [ ] Lancer une partie
4. [ ] Jouer une manche
5. [ ] À la fin de la manche, vérifier dans le tableau de bord:
   - [ ] Les scores s'actualisent automatiquement (pas besoin de rafraîchir)
   - [ ] Le classement est affiché correctement
   - [ ] Le message de classement s'affiche
6. [ ] Jouer 2 manches supplémentaires
7. [ ] Vérifier que les scores cumulés augmentent correctement

---

### Test 7: Stop/Pause du Jeu Pendant une Manche
**Objectif:** Vérifier que l'admin peut arrêter le jeu correctement

**Étapes:**
1. [ ] Lancer une partie
2. [ ] Une manche en cours
3. [ ] Depuis l'arbitre: cliquer "Pause"
4. [ ] Attendre 3 secondes (que la pause passe)
5. [ ] Vérifier:
   - [ ] Pas de nouvelle phrase envoyée
   - [ ] Logs affichent: `"Jeu n'est plus en mode 'playing'"`
6. [ ] Depuis l'arbitre: cliquer "Reset"
7. [ ] Vérifier:
   - [ ] Scores remis à 0
   - [ ] Manche revient à 0
   - [ ] État = "waiting"

---

### Test 8: Aide au Débogage - Vérifier les Messages WebSocket
**Objectif:** Vérifier que les bons messages sont envoyés

**Étapes:**
1. [ ] Lancer le serveur avec logs DEBUG: (vérifier `logger.py`)
2. [ ] Connecter 1 joueur
3. [ ] Lancer une manche et la terminer
4. [ ] Dans les logs, vérifier la séquence:
   ```
   [DEBUG] Résultat de manche reçu de pi-1
   [INFO] Fin de la manche ! Calcul du classement...
   [DEBUG] TOUS OUT {"type": "round_classement", "classement": [...], "global_scores": {...}}
   [DEBUG] TOUS OUT {"type": "player_update", "scores": {...}}
   [DEBUG] TOUS OUT {"type": "new_phrase", "phrase": "...", "round_number": 1}
   ```

---

## 📋 Résumé des Vérifications

### Tous les Tests Passés ✅
- [ ] Test 1: Partie sans BD - Scores s'actualisent
- [ ] Test 2: Partie avec BD - Scores sauvegardés
- [ ] Test 3: Déconnexion rapide - Pas de crash
- [ ] Test 4: Race condition - Scores corrects, pas dupliqués
- [ ] Test 5: Bonus/Malus - Pas de crash
- [ ] Test 6: Interface admin - Mise à jour en temps réel
- [ ] Test 7: Stop/Pause - Fonctionne correctement
- [ ] Test 8: Messages WebSocket - Séquence correcte

---

## 🐛 Si un Test Échoue

1. **Vérifier les logs du serveur:**
   ```bash
   # Augmenter le niveau de log dans logger.py ou app.py
   log_server(f"DEBUG: {variable}", "DEBUG")
   ```

2. **Activer les logs WebSocket détaillés:**
   - Voir `logger.py` pour activer `log_websocket()` en détail

3. **Vérifier la BD:**
   ```bash
   docker logs race-typer-db-1  # Voir les logs PostgreSQL
   docker exec -it race-typer-db-1 psql -U racetyper -d racetyper -c "SELECT * FROM round_results;"
   ```

4. **Vérifier la connexion du client:**
   - Voir si le client envoie bien le message `"action": "phrase_finished"`
   - Vérifier que le client reçoit bien les messages du serveur

---

## 📞 Aide Additionnelle

- **Logs détaillés:** Rechercher "DEBUG" ou "WARNING" dans la sortie serveur
- **Erreurs de syntaxe:** Vérifier avec `python -m py_compile server_app/GameManager.py`
- **Tests isolés:** Voir `tests/test_main.py` pour les tests unitaires
