# Backend Data Directory

Seed data files (`sources.json`, `seed_news.json`) live in the project root `data/` directory.

During Docker build, these files are copied into the backend container via the Dockerfile:

```dockerfile
COPY data/sources.json ./data/sources.json
COPY data/seed_news.json ./data/seed_news.json
```

The `docker-compose.yml` sets the build context to the project root so the backend Dockerfile can access both `backend/` and `data/` directories.

At runtime, the `data/` directory inside the container is mounted as a Docker volume (`db_data`) to persist the SQLite database (`briefwave.db`).
