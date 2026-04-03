# WebSocket et Django Channels

Cette application utilise **Django Channels** pour les communications temps réel. La configuration est exposée via l'ASGI `gasycar/asgi.py`, et les couches de canaux sont définies dans les settings. Deux domaines fonctionnels sont exposés : les notifications génériques et le support (messagerie des tickets).

## Configuration globale
- `ASGI_APPLICATION` pointe vers `gasycar.asgi.application`.
- `CHANNEL_LAYERS` utilise l'`InMemoryChannelLayer` par défaut, adapté au développement ou aux déploiements mono-instance. Pour un déploiement multi-instance, remplacer par Redis.
- Le routeur ASGI combine HTTP et WebSocket :
  - HTTP est servi par l'application Django standard.
  - WebSocket passe par `AllowedHostsOriginValidator` puis `AuthMiddlewareStack`, avant d'être routé vers les URL WebSocket de `notification` et `support`.
- Serveur : `daphne` est installé et doit être utilisé pour lancer l'ASGI app (ex. `daphne gasycar.asgi:application`).

## Endpoints WebSocket
### Notifications
- **URL** : `ws/notification/<room_name>/`
- **Consumer** : `notification.consumers.NotificationConsumer`
- **Type** : `WebsocketConsumer` (synchrone).
- **Groupes** : chaque client rejoint `notification_<room_name>` lors de la connexion, et est retiré à la déconnexion.
- **Réception côté serveur** : 
  - Attend un message JSON contenant la clé `"message"`.
  - Relaye ce dictionnaire sur le groupe via `group_send` avec l'événement `notification_message`.
- **Envoi vers le client** : 
  - La méthode `notification_message` renvoie le contenu de `message` tel quel en JSON.
- **Authentification** : aucune restriction explicite ; la pile d'auth Channels peut associer un utilisateur si une session Django valide est présente.

### Support (tickets)
- **URL** : `ws/support/tickets/<ticket_id>/`
- **Consumer** : `support.consumers.TicketConsumer`
- **Type** : `AsyncJsonWebsocketConsumer`.
- **Accès** : refuse la connexion (`close()`) si `scope['user']` est anonyme.
- **Groupes** : chaque socket rejoint `ticket_<ticket_id>` à la connexion et le quitte à la déconnexion.
- **Diffusion** : écoute l'événement `ticket_message` sur le groupe et transmet l'événement complet au client via `send_json` (utilisable pour pousser les nouveaux messages d'un ticket).

## Routage ASGI
Les routes WebSocket sont définies dans chaque application et agrégées dans `gasycar/asgi.py` :

```python
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(notifications_urlpatterns + support_urlpatterns)
            )
        ),
    }
)
```

## Points d'attention
- **Origines** : `AllowedHostsOriginValidator` applique la liste `ALLOWED_HOSTS`. Vérifier `ALLOWED_HOSTS` pour les environnements de prod.
- **Persistence** : l'`InMemoryChannelLayer` ne partage pas les messages entre workers. Utiliser Redis pour un déploiement multi-processus.
- **Authentification** : `AuthMiddlewareStack` prend en charge les sessions Django. Si des tokens JWT sont utilisés côté client, prévoir un middleware Channels compatible JWT.
- **Formats de message** : respecter les structures attendues par les consumers (`{"message": ...}` pour les notifications ; charge libre pour les tickets via `ticket_message`).
