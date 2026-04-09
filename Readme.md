modifier le rôle de Tina :
1.Entrer dans PostgreSQL
docker compose exec db psql -U postgres -d mcar

2.Voir toutes les tables
\dt

3.Voir la structure de la table des utilisateurs
\d users

4.Afficher la liste des utilisateurs (pour identifier Tina)
SELECT email, first_name, last_name, role 
FROM users 
ORDER BY date_joined DESC;

5.Modifier le rôle en ADMIN (la commande principale)
UPDATE users 
SET role = 'ADMIN'
WHERE email = 'tinalalaina14@gmail.com';

6.Vérifier que le changement a bien été fait
SELECT email, first_name, last_name, role 
FROM users 
WHERE email = 'tinalalaina14@gmail.com';
