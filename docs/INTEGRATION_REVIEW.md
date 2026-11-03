# Revue du fork MyLight Systems

Date : 2026-11-03. Base inspectée : e77319016fc13eb286aed6c78ce9d91e314668da.
Origine : https://github.com/acesyde/hassio_mylight_integration.

## Maintenance et attribution

Le domaine `mylight_systems` et les identifiants des entités restent identiques :
ce fork remplace l'intégration d'origine et ne doit pas être installé en parallèle.
Les liens d'installation HACS, la documentation, le suivi et les responsables
pointent vers azman0101. L'auteur d'origine reste déclaré dans pyproject.toml.
La licence MIT est inchangée ; licence et notice accompagnent aussi le composant.

## Sécurité : exposition des identifiants dans les journaux

Dans `api/client.py::_execute_request`, le journal de débogage utilisait
`response.url`. La requête de connexion contient `email` et `password`
dans sa query string ; les autres appels contiennent `authToken`.
Les erreurs aiohttp pouvaient également inclure ces URL dans leur message
et leur traceback, ensuite propagé vers Home Assistant.

Le débogage est recommandé dans les README pour le dépannage.
Un journal partagé avec un tiers pouvait donc exposer le mot de passe MyLight
ou un jeton permettant de consulter les données et de commander le relais.
L'impact potentiel est la compromission du compte ; l'exploitation nécessite
l'accès aux journaux concernés. Ce constat n'établit pas une attaque distante
sans authentification contre Home Assistant.

Correction : journaliser le chemin de l'endpoint et le statut, uniquement le type
d'erreur réseau, et supprimer la chaîne d'exception contenant l'URL lors de la
conversion en CommunicationError. Le protocole de l'API reste inchangé.
Trois cas de régression vérifient succès, erreur réseau et erreur HTTP.

## Revue de l'intégration

Inspection statique du config flow et de la réauthentification, de l'initialisation
et du déchargement, du coordinateur, du client HTTP, des entités, des diagnostics,
de l'export CSV, des dépendances et des trois workflows GitHub Actions.
Le client utilise HTTPS par défaut avec la vérification TLS d'aiohttp.
Les diagnostics masquent les identifiants de configuration et retirent authToken
des réponses API. Les dates de l'export sont validées et la plage limitée à 31 jours.
La suite couvre les API, les flows, les diagnostics, les capteurs, relais et exports.

Aucun autre problème justifiant une correction à impact critique n'a été confirmé
dans ce périmètre. Il s'agit d'une revue statique et de tests simulés, sans accès à
un compte MyLight réel, sans audit des dépendances transitives ni test d'intrusion
sur le service du fournisseur. La revue ne constitue pas une certification.

## Validation

- `uv sync --dev` à partir du lockfile existant.
- `python -m pytest` sous Python 3.14.8 : 99 tests réussis.
- Ruff lint et format sur les fichiers Python modifiés : réussis.
- Licence racine conservée à l'identique.
- JSON/TOML et `git diff --check` vérifiés.

Les issues du fork étaient désactivées au moment de la revue. Le lien
`issue_tracker` du manifeste désigne le futur suivi propre au fork, dont
l'activation reste un réglage GitHub. Les contrôles CI distants sont suivis dans la PR.
