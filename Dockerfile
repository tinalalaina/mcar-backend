# Utilisez une image de base qui inclut Python
FROM python:3.10

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Met à jour les paquets et installe les dépendances système nécessaires
RUN apt-get update && \
    apt-get install -y git libpq-dev ffmpeg

# Met à jour pip
RUN pip install --upgrade pip

# Copie les fichiers requis dans le conteneur
COPY requirements.txt /app/

# Installe les dépendances Python
RUN pip install -r requirements.txt

# Copie le reste des fichiers dans le conteneur
COPY . /app/

# Copie le script d'entrée dans le conteneur
# COPY entrypoint.sh /app/

# Rendre le script d'entrée exécutable
# RUN chmod +x /app/entrypoint.sh

# Définir le script d'entrée comme point d'entrée
# ENTRYPOINT ["/app/entrypoint.sh"]
# suppre
# Expose le port sur lequel Django écoute
EXPOSE 8000

# Commande pour démarrer le serveur Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]