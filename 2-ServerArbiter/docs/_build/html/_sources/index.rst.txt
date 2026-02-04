.. RaceTyper — Server Arbitre documentation master file

============================
RaceTyper — Server Arbitre
============================

Bienvenue dans la documentation du **serveur arbitre RaceTyper**.
Ce serveur gère la logique de jeu, les connexions WebSocket des joueurs
et l'interface d'administration en temps réel.

.. contents:: Table des matières
   :depth: 2
   :local:

Architecture
============

Le serveur est composé de quatre modules principaux :

+-------------------+-------------------------------------------------------+
| Module            | Rôle                                                  |
+===================+=======================================================+
| ``app``           | Point d'entrée FastAPI — routes et WebSockets         |
+-------------------+-------------------------------------------------------+
| ``GameManager``   | Cerveau du jeu — état, manches, scores                |
+-------------------+-------------------------------------------------------+
| ``ObjectManager`` | Gestion des bonus/malus dans les phrases              |
+-------------------+-------------------------------------------------------+
| ``logger``        | Logging coloré en console                             |
+-------------------+-------------------------------------------------------+

Référence API
=============

.. toctree::
   :maxdepth: 2

   modules/app
   modules/gamemanager
   modules/objectmanager
   modules/logger
