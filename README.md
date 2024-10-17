# lab4_simple
(Simple version) Lab 4 for PP.
# Project Setup
## Starting the Application
To start the application, follow these steps:

**Build and Start Containers**

- Run the following command to build and start all the Docker containers:

```sh
   docker compose up --build
```

- If you haven't made changes to the Docker setup or application code, you can restart the containers with:

```sh
    docker compose up
```

## Ports that used in app:

### For postgres (db):

- **5432:5432**

### For django (backend):

- **3000:3000**

### Notes:
- Ensure Docker and Docker Compose are installed and running on your machine.
- Adjust container names and paths according to your specific setup if they differ from the defaults.