# Rapport de tests - Agent Support Client

Date: 2026-10-27 12:07 | Mode: mock LLM (déterministe) | Durée: 240 s

## Résultat global: SUCCÈS - 29/29 cas réussis (100 %)

Non-régression: aucune régression par rapport à la référence

## Par type de test

| Type | Réussis | Total |
|---|---|---|
| Format (sorties) | 6 | 6 |
| Intégration (enchaînements) | 7 | 7 |
| Policy (règles) | 9 | 9 |
| Mauvaise entrée (robustesse) | 7 | 7 |

## Détail des cas

| ID | Type | Cas | Résultat | Durée |
|---|---|---|---|---|
| F01 | format | Réponse avec ligne de trace (REQ, statut, durée, étapes) | PASS | 61.8 s |
| F02 | format | La trace liste l'étape LLM et l'étape outil | PASS | 61.8 s |
| F03 | format | Ticket: identifiant TCK-xxxxxx et colonnes de tickets.csv | PASS | 61.8 s |
| F04 | format | executions.csv: colonnes attendues et fichier valide | PASS | 61.8 s |
| F05 | format | steps.csv: colonnes attendues et fichier valide | PASS | 26.5 s |
| F06 | format | Dashboard: KPIs et tableau des exécutions | PASS | 45.7 s |
| I01 | integration | Suivi de commande: l'agent appelle l'outil Statut commande | PASS | 26.4 s |
| I02 | integration | Question générale: l'agent appelle l'outil FAQ | PASS | 26.4 s |
| I03 | integration | Plainte: ticket créé et lié au Correlation ID | PASS | 26.3 s |
| I04 | integration | Salutation: aucun outil appelé, une seule étape | PASS | 26.1 s |
| I05 | integration | Le Correlation ID affiché est celui écrit dans executions.csv | PASS | 26.1 s |
| I06 | integration | Le dashboard liste les requêtes précédentes (même Correlation ID) | PASS | 79.5 s |
| I07 | integration | /dashboard n'appelle jamais le LLM (routage If-Else) | PASS | 20.7 s |
| P01 | policy | Email masqué dans les logs | PASS | 27.9 s |
| P02 | policy | Numéro de carte masqué dans les logs | PASS | 27.8 s |
| P03 | policy | Mot de passe masqué dans les logs | PASS | 28.3 s |
| P04 | policy | La clé API n'est jamais écrite dans les logs | PASS | 27.5 s |
| P05 | policy | Alerte Latence quand la moyenne dépasse 5000 ms | PASS | 19.4 s |
| P06 | policy | Alerte Taux d'échec quand plus de 20 % d'erreurs | PASS | 24.1 s |
| P07 | policy | Alerte Coût quand le budget de 0,50 USD est dépassé | PASS | 23.7 s |
| P08 | policy | Aucune alerte quand tout va bien | PASS | 22.2 s |
| P09 | policy | L'alerte s'affiche aussi sous la réponse de l'agent | PASS | 24.6 s |
| B01 | mauvaise_entree | Commande inconnue: réponse propre, pas d'erreur système | PASS | 24.2 s |
| B02 | mauvaise_entree | Panne de l'outil commande (mock panne): statut erreur tracé | PASS | 24.1 s |
| B03 | mauvaise_entree | Outil lent (mock timeout): durée de l'outil mesurée (>= 3,5 s) | PASS | 26.7 s |
| B04 | mauvaise_entree | Message très long (5000 caractères): pas de crash | PASS | 24.4 s |
| B05 | mauvaise_entree | Texte de type injection SQL: pas de crash, logs intacts | PASS | 23.9 s |
| B06 | mauvaise_entree | Message en arabe: traité et loggé en Unicode | PASS | 23.8 s |
| B07 | mauvaise_entree | Panne de l'outil FAQ (mock panne): statut erreur tracé | PASS | 21.3 s |
