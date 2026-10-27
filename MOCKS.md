# Documentation des mocks utilisés

Un mock remplace un service externe par une version contrôlée, pour reproduire des cas rares (panne, lenteur) et obtenir des tests **déterministes, gratuits et rapides**.

## Mocks disponibles

| Mock | Où | Ce qu'il simule | Comment l'activer |
|---|---|---|---|
| **Mock LLM** | `tests/mock_llm.py` (serveur compatible OpenAI) | Le modèle de langage de l'agent, avec appels d'outils | Automatique en CI: `make_test_flow.py` remplace le noeud OpenRouter par ce serveur local |
| **Mock outil: Succès** | Noeud « Correlation ID », Simulation = `aucune` | Les 3 outils répondent normalement | Valeur par défaut |
| **Mock outil: Timeout** | Simulation = `latence` | Chaque outil met 4 s à répondre | Cas `B03` |
| **Mock outil: Panne (erreur 500)** | Simulation = `erreur` | Chaque outil échoue (« service indisponible ») | Cas `B02`, `B07` |
| **Mock historique** | `seed` dans un cas de test | Un `executions.csv` pré-rempli pour déclencher les alertes | Cas `P05` à `P09` |

## Règles du Mock LLM (déterministe)
Sur le dernier message client: `CMD-xxxx` → outil Statut commande; « plainte », « litige », « problème » → outil Créer un ticket; « retour », « livraison », « garantie » → outil FAQ; sinon → salutation. Après un appel d'outil, il répond « Resultat: » suivi du résultat de l'outil. Chaque requête reçue est journalisée (`MOCK_LOG`), ce qui permet de prouver que le LLM n'est jamais appelé pour `/dashboard`.

## Ce que les mocks permettent de tester, et ce qu'ils ne testent pas
- **Testé avec mock**: câblage du workflow, routage If-Else, appels d'outils, Correlation ID, écriture et format des logs, masquage des données sensibles, alertes, dashboard, comportement en cas de panne ou de lenteur, entrées anormales.
- **Non testé avec mock**: la qualité et le choix des outils du **vrai modèle** (le mock applique des règles fixes). C'est le rôle des cas `L01` à `L06`, exécutés avec un vrai modèle (`--live`, clé `OPENROUTER_API_KEY`), hors du pipeline principal.
