"""
Test rapide du serveur d'inférence - vérifie que l'IA fonctionne correctement
"""

import requests
import json

def test_ai_server():
    server_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        health_resp = requests.get(f"{server_url}/health")
        print(f"Health check: {health_resp.json()}")
    except Exception as e:
        print(f"❌ Serveur non disponible: {e}")
        return
    
    # Test quelques prédictions
    test_chars = ['a', 'e', 'l', ' ', 'H']
    CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!"
    
    print("\n🤖 Test de prédictions IA:")
    for char in test_chars:
        try:
            char_index = CHARS.index(char)
            resp = requests.post(f"{server_url}/predict", 
                               json={"obs": char_index})
            
            if resp.ok:
                result = resp.json()
                predicted_char = result['char']
                action = result['action']
                correct = predicted_char == char
                status = "✅" if correct else "❌"
                print(f"  {status} Cible: '{char}' → IA prédit: '{predicted_char}' (action: {action})")
            else:
                print(f"  ❌ Erreur API: {resp.status_code}")
        except Exception as e:
            print(f"  ❌ Erreur pour '{char}': {e}")

if __name__ == "__main__":
    test_ai_server()