# Rapport de tests - Agent Support Client

Date: 2026-10-27 11:17 | Mode: mock LLM (déterministe) | Durée: 158 s

## Résultat global: ÉCHEC - 26/29 cas réussis (90 %)

Non-régression: RÉGRESSIONS: P01, P02, P03

## Par type de test

| Type | Réussis | Total |
|---|---|---|
| Format (sorties) | 6 | 6 |
| Intégration (enchaînements) | 7 | 7 |
| Policy (règles) | 6 | 9 |
| Mauvaise entrée (robustesse) | 7 | 7 |

## Détail des cas

| ID | Type | Cas | Résultat | Durée |
|---|---|---|---|---|
| F01 | format | Réponse avec ligne de trace (REQ, statut, durée, étapes) | PASS | 35.2 s |
| F02 | format | La trace liste l'étape LLM et l'étape outil | PASS | 35.1 s |
| F03 | format | Ticket: identifiant TCK-xxxxxx et colonnes de tickets.csv | PASS | 35.5 s |
| F04 | format | executions.csv: colonnes attendues et fichier valide | PASS | 35.1 s |
| F05 | format | steps.csv: colonnes attendues et fichier valide | PASS | 35.3 s |
| F06 | format | Dashboard: KPIs et tableau des exécutions | PASS | 60.1 s |
| I01 | integration | Suivi de commande: l'agent appelle l'outil Statut commande | PASS | 29.9 s |
| I02 | integration | Question générale: l'agent appelle l'outil FAQ | PASS | 29.7 s |
| I03 | integration | Plainte: ticket créé et lié au Correlation ID | PASS | 29.7 s |
| I04 | integration | Salutation: aucun outil appelé, une seule étape | PASS | 29.7 s |
| I05 | integration | Le Correlation ID affiché est celui écrit dans executions.csv | PASS | 29.9 s |
| I06 | integration | Le dashboard liste les requêtes précédentes (même Correlation ID) | PASS | 83.9 s |
| I07 | integration | /dashboard n'appelle jamais le LLM (routage If-Else) | PASS | 24.8 s |
| P01 | policy | Email masqué dans les logs | **FAIL** | 29.4 s |
| P02 | policy | Numéro de carte masqué dans les logs | **FAIL** | 29.5 s |
| P03 | policy | Mot de passe masqué dans les logs | **FAIL** | 29.5 s |
| P04 | policy | La clé API n'est jamais écrite dans les logs | PASS | 29.7 s |
| P05 | policy | Alerte Latence quand la moyenne dépasse 5000 ms | PASS | 24.8 s |
| P06 | policy | Alerte Taux d'échec quand plus de 20 % d'erreurs | PASS | 24.7 s |
| P07 | policy | Alerte Coût quand le budget de 0,50 USD est dépassé | PASS | 24.6 s |
| P08 | policy | Aucune alerte quand tout va bien | PASS | 24.6 s |
| P09 | policy | L'alerte s'affiche aussi sous la réponse de l'agent | PASS | 29.5 s |
| B01 | mauvaise_entree | Commande inconnue: réponse propre, pas d'erreur système | PASS | 29.3 s |
| B02 | mauvaise_entree | Panne de l'outil commande (mock panne): statut erreur tracé | PASS | 28.5 s |
| B03 | mauvaise_entree | Outil lent (mock timeout): durée de l'outil mesurée (>= 3,5 s) | PASS | 31.8 s |
| B04 | mauvaise_entree | Message très long (5000 caractères): pas de crash | PASS | 28.2 s |
| B05 | mauvaise_entree | Texte de type injection SQL: pas de crash, logs intacts | PASS | 26.6 s |
| B06 | mauvaise_entree | Message en arabe: traité et loggé en Unicode | PASS | 14.0 s |
| B07 | mauvaise_entree | Panne de l'outil FAQ (mock panne): statut erreur tracé | PASS | 13.8 s |

## Échecs

### P01 - Email masqué dans les logs
- csv_not_contains: texte interdit dans les logs: 'test@mail.com'
- csv_contains: texte attendu dans les logs: '[EMAIL]'
- Extrait de la réponse: `Resultat: {"statut": "en_preparation", "detail": "En preparation, expedition prevue demain."}  --- `REQ-7F3419` · succes · 3990 ms · 2 étapes · ~$0.000139 (tokens estimés) - 🧠 `agent_llm (2 appels)` 3`
### P02 - Numéro de carte masqué dans les logs
- csv_not_contains: texte interdit dans les logs: '4111 1111 1111 1111'
- Extrait de la réponse: `Resultat: {"ticket_id": "TCK-A00D59", "statut": "cree", "message": "Un conseiller vous recontactera sous 24h."}  --- `REQ-F1D3B5` · succes · 3993 ms · 2 étapes · ~$0.000164 (tokens estimés) - 🧠 `agent`
### P03 - Mot de passe masqué dans les logs
- csv_not_contains: texte interdit dans les logs: 'Secret123'
- csv_contains: texte attendu dans les logs: '[SECRET]'
- Extrait de la réponse: `Resultat: {"statut": "en_preparation", "detail": "En preparation, expedition prevue demain."}  --- `REQ-DF3C2B` · succes · 3936 ms · 2 étapes · ~$0.000139 (tokens estimés) - 🧠 `agent_llm (2 appels)` 3`
