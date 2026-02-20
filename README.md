# BOTSLOP
This project has two parts:

- Backend: A Flask API that scrapes Reddit comments, classifies them using a Hugging Face model, and stores results in a SQLite database.

- Frontend: A React app that fetches data from the backend and displays comments.

## Backend
Built with Flask + SQLite.

Provides endpoints:

/data → returns the latest comments from the database.

/scrape → scrapes Reddit, classifies comments, and stores results.

/health → simple health check for Docker Compose.

### Frontend
Built with React.

Fetches data from the backend via api.js.


### Docker Compose - Dev Workflow
docker-compose.yml defines both services:

- backend (Flask API)

- frontend (React app)

Run everything together:

```
docker-compose up --build
```

Backend is accessible at http://localhost:5050, frontend at http://localhost:3000.

### Development Workflow
For quick iteration:

Backend mounts source code as a volume and runs Flask with --reload.

Frontend mounts source code and uses React’s hot reload.

Logs are verbose — backend logs show model download progress and classification steps.

Health checks are configured so Docker knows if the backend is alive.


### Nuances
The Hugging Face model (eevvgg/StanceBERTa) is large and may take time to download the first time.

To avoid runtime download issues, you can pre‑download the model in the Docker build step.

CORS must be enabled (flask-cors) so the React frontend can call the API from another port.

In Docker Compose, the backend listens on port 5000 internally, mapped to 5050 externally.


