# Sevinteam Hotel Reservation System

This project belongs to the Sevin team. It is an online hotel reservation application implemented using Django. We initiated this project on feb 2, 2025, and completed it by feb 2, 2025. The project is built using Redis, Celery, and PostgreSQL architectures.

Deployment Instructions
To deploy this project on your server, you need to carefully follow these steps.

Prerequisites
Firstly, ensure Docker and Docker Compose are installed on your server. You can install them using the following commands:


```
sudo apt update
sudo apt install docker.io
sudo apt install docker-compose
```

For better performance, it's recommended to use Nginx as the web server. Install Nginx using:

```
sudo apt install nginx
```

Using Docker
To deploy using Docker, follow these steps:

Clone the Repository:

```
git clone <repository-url>
cd <repository-name>
```
Build and Run Docker Containers:

```
sudo docker-compose up --build
```

Using Server Installation Commands
If you prefer to set up the environment without Docker, follow these general steps:

Clone the Repository:

```
git clone <repository-url>
cd <repository-name>
```

Install Required Python Packages:

```
pip install -r requirements.txt
```

Apply Database Migrations:

```
python manage.py migrate
```

Start the Django Server:

```
python manage.py runserver
```

Configuration
Before running the project, ensure you've configured the following:

Database settings: Update your PostgreSQL database settings in the Django settings.py file.
Redis and Celery settings: Ensure your Redis and Celery configurations are correctly set in the Django settings.py file.
Nginx Configuration: Configure Nginx to proxy pass to your Django application.
Uploading to GitHub
To properly document and share these deployment instructions on GitHub, create a README.md file in your repository and include the above content in English. Use the following commands to add the file to your GitHub repository:

```
git add README.md
git commit -m "Add deployment instructions and prerequisites"
git push origin master
```

These commands add the README.md file to your repository, commit it, and push it to the master branch on GitHub. Now, others can easily use this guide to deploy and utilize your project.


# Design by sevinteam
