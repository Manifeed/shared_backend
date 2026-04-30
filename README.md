# shared_backend

Package backend partageable entre les microservices Manifeed.

## Ce qui appartient ici

Le package ne contient que des briques transverses sans accès DB ni logique
métier dépendante d'un service précis :

- erreurs applicatives et handlers communs ;
- schémas Pydantic d'API et de payloads inter-services ;
- helpers de domaine purs (`password_policy`, `user_identity`, `current_user`, `worker_identity`) ;
- utilitaires de sécurité pour mots de passe, sessions, API keys et secrets ;
- sécurité de communication inter-services ;
- helpers de clients HTTP internes réutilisables.

Les services gardent leurs clients DB, leurs repositories et leur orchestration
métier locale.

## Règle de mutualisation

- Si un contrat ou un helper est utilisé par au moins 2 services, il entre dans `shared_backend`.
- Si le code dépend d'une base, d'un endpoint spécifique, d'un workflow métier ou d'une intégration externe propre à un service, il reste local.

## Workflow de changement

1. Modifier le schéma ou helper partagé dans `shared_backend`.
2. Adapter les producteurs et consommateurs concernés.
3. Ajouter ou mettre à jour les tests de contrat.
4. Incrémenter la version `shared_backend` dans `pyproject.toml`.

## Build

Les images Docker backend construisent désormais une wheel locale
`manifeed-shared-backend` depuis le monorepo, puis l'installent dans chaque
image. Il n'y a plus de dépendance GitHub requise au build.
