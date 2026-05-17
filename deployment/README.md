# Deployment Guide

This folder contains a Docker-based deployment starter for the project.

Files:

- `backend.Dockerfile`: builds the FastAPI backend image
- `frontend.Dockerfile`: builds the React frontend and serves it through Nginx
- `docker-compose.yml`: runs frontend and backend together
- `nginx.conf`: serves the SPA and proxies `/api/*` to the backend
- `.env.example`: deployment-time environment template

## Quick Start

1. Copy `deployment/.env.example` to `deployment/.env`.
2. Fill in the required secrets for Supabase, Cohere, Qdrant, Groq, and SMTP.
3. From the `deployment/` directory run:

```powershell
docker compose up --build -d
```

Frontend:

```text
http://localhost:8080
```

Backend API:

```text
http://localhost:8000
```

## Notes

- The frontend is built with `/api` as the backend base URL and Nginx proxies requests to the backend container.
- Generated proposals are stored in `generated_proposals/` on the host through a bind mount.
- Uploaded tenders are stored in `uploaded_pdfs/` on the host through a bind mount.
- External services such as Supabase, Qdrant, and SMTP are expected to be managed outside this compose stack.
