# Aevix Production Deployment Manual

This document provides comprehensive guides and instructions for deploying Aevix to a production environment using Docker Compose.

---

## 1. Prerequisites

Before starting, ensure your target host (Linux VPS, AWS EC2, DigitalOcean droplet, etc.) has the following:

- **Operating System:** Ubuntu 22.04 LTS or newer recommended.
- **Docker:** v24.0.0 or newer.
- **Docker Compose:** v2.20.0 or newer.
- **Hardware Resources:** Minimum 2 vCPUs, 4GB RAM, and 20GB disk storage recommended.
- **Networking:** Ports `80` and `443` open and forwarded on public interfaces.
- **DNS Configuration:** A wildcard or A/AAAA record pointing your domain (e.g. `app.aevix.ai`) to the host's public IP.

---

## 2. Step-by-Step Installation

### Step 2.1: Clone the Repository
Clone the codebase to your server:
```bash
git clone https://github.com/mukeshkumarv2005/aixeu-ai.git aevix
cd aevix
```

### Step 2.2: Configure Environment Variables
Copy the production environment template:
```bash
cp docker/production.env.template .env
```
Open `.env` and configure the required keys:
```ini
# Application configuration
APP_ENV=production
APP_DEBUG=false
ASYNC_WORKERS=true

# Security secrets (Use openssl rand -hex 32 to generate)
SECRET_KEY=your_generated_long_random_jwt_secret_key

# PostgreSQL database secrets
POSTGRES_USER=aevix
POSTGRES_PASSWORD=your_strong_db_password
POSTGRES_DB=aevix

# Redis secrets
REDIS_PASSWORD=your_strong_redis_password

# AI Provider API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Step 2.3: Build & Start Containers
Launch the application infrastructure:
```bash
docker compose build
docker compose up -d
```
Verify that all services are running:
```bash
docker compose ps
```

---

## 3. HTTPS & Let's Encrypt SSL Setup

We provide an automated script to handle Let's Encrypt certificate registration and Nginx integration.

### Step 3.1: Execute SSL Bootstrapper
Run the following script as root:
```bash
sudo ./scripts/setup_ssl.sh
```
This script will:
1. Ask for your domain name (e.g. `app.aevix.ai`) and email address.
2. Bootstrap a temporary self-signed certificate so Nginx starts.
3. Use Certbot to request a real SSL certificate from Let's Encrypt.
4. Replace the temporary files and reload Nginx.

### Step 3.2: Configure Automatic SSL Renewal
To keep Let's Encrypt certificates updated automatically, configure a cron job to run once a day:
```bash
sudo crontab -e
```
Add the following line at the bottom:
```cron
0 0 * * * cd /path/to/aevix && docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/lib/letsencrypt:/var/lib/letsencrypt -v $(pwd)/storage/certbot:/var/www/certbot certbot/certbot renew --webroot -w /var/www/certbot && docker compose exec -T nginx nginx -s reload
```

---

## 4. Database Migrations

Database schema updates and migrations are handled automatically.
- The `backend` and `worker` containers use the [entrypoint.sh](file:///c:/Users/HP/aevix/backend/entrypoint.sh) script.
- On startup, it waits for PostgreSQL to be healthy, executes `alembic upgrade head` to run pending migrations, and verifies that the `pgvector` extension is registered in the database.
- If you need to manually inspect migrations, use:
  ```bash
  docker compose exec backend alembic current
  docker compose exec backend alembic history
  ```

---

## 5. Automated Backups & Restoration

We include backup scripts located in the `scripts/` folder.

### Step 5.1: Executing Backups
To run a manual backup of your database, config, and upload storage:
```bash
./scripts/backup.sh
```
Backups are saved as compressed files under `/var/backups/aevix/backup_YYYYMMDD_HHMMSS.tar.gz`.

### Step 5.2: Scheduling Backups (Cron)
Configure a nightly backup cron job:
```bash
crontab -e
```
Add the following line to run a backup every night at 2:00 AM:
```cron
0 2 * * * cd /path/to/aevix && ./scripts/backup.sh > /dev/null 2>&1
```

### Step 5.3: Restoring a Backup
To restore database states and storage assets from a backup file:
```bash
./scripts/restore.sh /var/backups/aevix/backup_20260705_120000.tar.gz
```
The script will prompt you for approval before writing configurations, restoring the SQL dump, and recreating folders.

---

## 6. Updating the Application

To perform zero-downtime updates:
1. Pull the latest commits from Git:
   ```bash
   git pull origin main
   ```
2. Build updated Docker images:
   ```bash
   docker compose build
   ```
3. Restart containers sequentially (Docker Compose applies migrations automatically during backend startup):
   ```bash
   docker compose up -d
   ```

---

## 7. Rollback Procedures

If an update fails and you need to roll back to a previous database and application state:

1. Stop active services:
   ```bash
   docker compose down
   ```
2. Restore database and uploads from the most recent backup:
   ```bash
   ./scripts/restore.sh /var/backups/aevix/backup_before_failed_update.tar.gz
   ```
3. Boot the application using the restored configurations:
   ```bash
   docker compose up -d
   ```

---

## 8. Logging & Troubleshooting

### Inspect Container Logs
To inspect logs of all services or specific containers:
```bash
# All logs
docker compose logs -f

# Backend logs only
docker compose logs -f backend

# Worker logs only
docker compose logs -f worker
```

### Common Issues & Resolutions

1. **Nginx startup fails with SSL file error:**
   Make sure you ran the `scripts/setup_ssl.sh` script to obtain and register SSL certificates.
2. **Database connection failures:**
   Ensure that the `POSTGRES_PASSWORD` configured in `.env` matches the connection URL and that the `postgres` database container health status is `healthy`.
3. **OpenAI / Embedding errors:**
   Ensure `OPENAI_API_KEY` is set and valid in `.env` when using `openai` as default provider or embedder.
