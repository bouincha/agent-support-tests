# Agent Support Client: tests automatisés et CI/CD (Atelier Jour 22)

![CI](https://github.com/VOTRE-COMPTE/VOTRE-REPO/actions/workflows/ci.yml/badge.svg)

> Remplacer `VOTRE-COMPTE/VOTRE-REPO` par votre dépôt GitHub: le badge devient vert quand la suite passe.

## Principe (low-code)
L'agent reste un **workflow Langflow** (aucun code d'agent). Les tests sont des **données**: `tests/golden_cases.json` décrit chaque cas (message, réglages, vérifications). Un runner générique lance le flow en mode headless (`lfx run`), vérifie les règles et produit un rapport. Pour ajouter un test, on ajoute un bloc JSON, pas du code.

```
flows/    Export Langflow du workflow (Support_Client_Observable_patched.json)
tests/    golden_cases.json (cas) | run_tests.py (runner + scorer) | mock_llm.py | make_test_flow.py
reports/  report.md, report.json, junit.xml (+ exemple de régression détectée)
.github/workflows/ci.yml   pipeline GitHub Actions
MOCKS.md  documentation des mocks
```

## Les 4 types de tests (cours) et leur couverture
| Type | Cas | Exemples |
|---|---|---|
| Format (sorties) | F01-F06 | ligne de trace, colonnes de executions.csv / steps.csv / tickets.csv, structure du dashboard |
| Intégration (enchaînements) | I01-I07 | commande vers outil commande, plainte vers ticket lié au Correlation ID, `/dashboard` sans appel LLM |
| Policy (règles) | P01-P09 | email, carte, mot de passe et clé API jamais loggés; 3 alertes (latence, échec, coût) |
| Mauvaise entrée (robustesse) | B01-B07 | commande inconnue, panne d'outil, outil lent, message de 5000 caractères, injection SQL, arabe |

**29 cas déterministes** (CI) + **6 cas live** (L01-L06, vrai modèle: choix des outils, absence d'hallucination, résistance à l'injection de prompt).

## Lancer les tests
```bash
pip install -r requirements-ci.txt
python tests/run_tests.py                    # suite avec mock LLM (aucune clé, ~3 min)
python tests/run_tests.py --only P01,I03     # certains cas
export OPENROUTER_API_KEY=sk-or-...; python tests/run_tests.py --live   # cas live
python tests/run_tests.py --update-baseline  # enregistre la référence de non-régression
```
Rapport: `reports/report.md`. Code de sortie 1 si un cas échoue ou si un cas qui passait avant échoue maintenant (**non-régression**: `tests/baseline.json`).

## Pipeline CI/CD (GitHub Actions)
`push` → installation → validation du JSON → suite de tests → rapport publié (artefact + résumé dans l'onglet Actions) → build rouge si un test échoue. Le job `tests-live` (vrai modèle) ne tourne que sur déclenchement manuel ou chaque lundi, avec le secret `OPENROUTER_API_KEY`.

Mise en route: créer le dépôt, pousser ce dossier, vérifier l'onglet **Actions**, puis copier le badge ci-dessus.

## Exemple de régression détectée
`reports/demo_regression_masquage_casse.md`: une modification casse le masquage des données sensibles; la suite passe de 29/29 à 26/29 et signale **P01, P02, P03** comme régressions.

## Ce que cette suite prouve, et ses limites
- Avec le mock, on valide le **workflow** (câblage, outils, logs, masquage, alertes, pannes), pas l'intelligence du modèle.
- La qualité du modèle réel est couverte par les cas live, qui n'ont **pas encore été exécutés** (pas de clé dans l'environnement de développement).
- Le fichier `ci.yml` n'a pas encore tourné sur GitHub: les mêmes commandes ont été exécutées en local.
- Après toute modification du flow dans Langflow: ré-exporter le JSON dans `flows/`, relancer les tests, committer.
