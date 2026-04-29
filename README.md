# shared_backend

Package backend partageable entre les microservices Manifeed.

Il contient uniquement la logique sans accès base de données:

- erreurs applicatives et exception handlers FastAPI;
- schemas Pydantic d'API et de payloads internes;
- helpers de domaine purs (`password_policy`, `user_identity`, `current_user`, `worker_identity`);
- utilities de sécurité pour hash de mots de passe, tokens de session, API keys et secrets.

Les services gardent leurs clients DB et networking locaux. Ce package sert de source unique pour les contrats et règles réutilisables.
