# Railway Deployment Guide — SentinelFlow AI

This guide documents the step-by-step non-Docker deployment path for SentinelFlow AI to Railway, including environment variables, database migrations, and troubleshooting guides.

---

## 1. Prerequisites
- A GitHub repository containing the project files.
- A Railway account.

## 2. Step-by-Step Railway Deployment

### Step 2.1: Create the Project
1. Log into your Railway console.
2. Select **New Project** → **Deploy from GitHub repository**.
3. Choose the `sentinelflow-ai` repository.

### Step 2.2: Add Database Services
1. Click **+ New** in your project view.
2. Choose **Database** → **Add PostgreSQL**.
3. Click **+ New** again, choose **Database** → **Add Redis**.

### Step 2.3: Configure Service Variables
Configure the primary application service with the following variables:

| Variable | Description | Recommended Value |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL Connection URI | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | Redis Connection URI | `${{Redis.REDIS_URL}}` |
| `ENVIRONMENT` | Environment tier selector | `production` |
| `DEBUG` | Enable verbose debugging | `false` |
| `SECRET_KEY` | JWT signing password | *Secure random string* |
| `ENCRYPTION_KEY` | AES encryption passcode | *Secure 32-character string* |
| `PORT` | Serves port binding | `8000` |

### Step 2.4: Deploy
Railway automatically builds and boots the application using the configuration in [railway.json](file:///e:/SENTINELFLOW%20AI/railway.json).

---

## 3. Post-Deployment Database Initialization
If migrations need to be forced manually:
1. Install the Railway CLI.
2. Execute the migration upgrade directly against production:
   ```bash
   railway run alembic -c backend/alembic.ini upgrade head
   ```

---

## 4. Troubleshooting Guide

### 4.1. "table already exists" migrations error
If you experience database migration conflicts, check if tables were auto-created by the app runtime lifespan. Ensure Alembic migrations are stamped to the matching head:
```bash
railway run alembic -c backend/alembic.ini stamp head
```

### 4.2. Connection Pool exhaustions
If database connection limits are exceeded in production, adjust the following parameters:
- `DATABASE_POOL_SIZE`: Lower it to `10` or `5` (default: 20).
- `DATABASE_MAX_OVERFLOW`: Lower to `5`.
