# docs/conf.py — Configuration Sphinx pour RaceTyper Server Arbitre
import os, sys

# Ajoute le répertoire parent (2-ServerArbiter/) au path
# pour que autodoc puisse importer server_app
sys.path.insert(0, os.path.abspath(".."))

# --- Infos projet ---
project = "RaceTyper — Server Arbitre"
copyright = "2025, Équipe RaceTyper"
author = "Équipe RaceTyper"
release = "1.0"

# --- Extensions ---
extensions = [
    "sphinx.ext.autodoc",       # Génère la doc à partir des docstrings
    "sphinx.ext.napoleon",      # Support Google-style & NumPy-style docstrings
    "sphinx.ext.viewcode",      # Ajoute des liens vers le code source
]

# Napoleon : on utilise le style Google
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Autodoc : montre les membres publics par défaut
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# Mock des dépendances tierces absentes dans cet env
# (autodoc ne peut pas importer app.py sans fastapi)
autodoc_mock_imports = ["fastapi", "fastapi.staticfiles", "fastapi.responses", "websockets"]

# --- Theme visuel ---
html_theme = "sphinx_rtd_theme"
html_theme_options = {}

# --- Fichiers statiques (optionnel) ---
html_static_path = []

# Fichier de départ
master_doc = "index"
