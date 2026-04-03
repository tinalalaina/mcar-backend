#!/bin/bash
set -e

# Appliquer les migrationssss
echo "Appliquer les migrations..."
python manage.py makemigrations
python manage.py migrate
# create default user
python manage.py create_default_admin
python manage.py create_default_client
python manage.py create_default_prestataire
python manage.py create_default_support

# data of model
python manage.py add_vehicule_equipments
python manage.py seed_vehicule_data

# vehicule data
python manage.py create_default_blog
python manage.py create_blog_roadtrip
python manage.py create_blog_itineraires


# Démarrer le serveur Django
echo "Démarrer le serveur Django..."
exec "$@"
