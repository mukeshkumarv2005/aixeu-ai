#!/usr/bin/env bash
# Aevix Production Backup Utility
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/aevix}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_DIR="$BACKUP_DIR/backup_$TIMESTAMP"

mkdir -p "$RUN_DIR"

echo "=== Aevix Automated Backup System ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup Directory: $RUN_DIR"
echo ""

# 1. Back up database
echo "→ Backing up PostgreSQL database..."
DB_USER="aevix"
DB_NAME="aevix"
if [ -f .env ]; then
  DB_USER=$(grep -E "^POSTGRES_USER=" .env | cut -d'=' -f2 || echo "aevix")
  DB_NAME=$(grep -E "^POSTGRES_DB=" .env | cut -d'=' -f2 || echo "aevix")
fi

# Perform containerized pg_dump (custom archive format)
docker exec -t aevix-postgres pg_dump -U "$DB_USER" -F c -d "$DB_NAME" > "$RUN_DIR/database.dump"
echo "  PostgreSQL database dump created!"

# 2. Back up uploaded files
echo "→ Backing up user uploads..."
if [ -d "backend/storage" ]; then
  tar -czf "$RUN_DIR/uploads.tar.gz" -C backend storage/
  echo "  User uploads backed up from local folder!"
elif docker volume inspect aevix_aevix_storage >/dev/null 2>&1; then
  docker run --rm -v aevix_aevix_storage:/volume -v "$RUN_DIR:/backup" alpine tar -czf /backup/uploads.tar.gz -C /volume .
  echo "  User uploads backed up from named volume!"
else
  echo "  Warning: No upload storage directory or volume found to back up."
fi

# 3. Back up config (.env)
if [ -f .env ]; then
  cp .env "$RUN_DIR/env.bak"
  echo "  Configuration (.env) backed up!"
fi

# 4. Tar the whole run folder and compress it
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" "backup_$TIMESTAMP"
rm -rf "$RUN_DIR"

echo "→ Backup archive created: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"

# 5. Retention policy: delete backups older than 7 days
echo "→ Applying retention policy (keeping last 7 days)..."
find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f -mtime +7 -delete
echo "Retention check completed!"
echo "Backup finished successfully!"
