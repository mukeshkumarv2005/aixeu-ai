#!/usr/bin/env bash
# Aevix Production Restoration Utility
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path_to_backup_tar_gz>"
  exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file '$BACKUP_FILE' does not exist."
  exit 1
fi

EXTRACT_DIR="/tmp/aevix_restore_$(date +%s)"
mkdir -p "$EXTRACT_DIR"

echo "=== Aevix Database & Storage Restore System ==="
echo "Extracting backup archive to $EXTRACT_DIR..."
tar -xzf "$BACKUP_FILE" -C "$EXTRACT_DIR"

# Find the backup directory name
BACKUP_FOLDER=$(ls "$EXTRACT_DIR" | grep "backup_" | head -n 1 || echo "")
if [ -z "$BACKUP_FOLDER" ]; then
  echo "Error: Invalid backup structure."
  rm -rf "$EXTRACT_DIR"
  exit 1
fi
SRC_DIR="$EXTRACT_DIR/$BACKUP_FOLDER"

# 1. Restore configuration
if [ -f "$SRC_DIR/env.bak" ]; then
  read -rp "Restore configuration (.env)? [y/N]: " RESTORE_ENV
  if [[ "$RESTORE_ENV" =~ ^[Yy]$ ]]; then
    cp "$SRC_DIR/env.bak" .env
    echo "  Configuration (.env) restored!"
  fi
fi

# Load database details
DB_USER="aevix"
DB_NAME="aevix"
if [ -f .env ]; then
  DB_USER=$(grep -E "^POSTGRES_USER=" .env | cut -d'=' -f2 || echo "aevix")
  DB_NAME=$(grep -E "^POSTGRES_DB=" .env | cut -d'=' -f2 || echo "aevix")
fi

# 2. Restore database
if [ -f "$SRC_DIR/database.dump" ]; then
  echo "→ Restoring database..."
  # Drop and recreate schema inside container
  docker exec -i aevix-postgres psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE);"
  docker exec -i aevix-postgres psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";"
  
  # Restore the pg_dump custom archive
  docker exec -i aevix-postgres pg_restore -U "$DB_USER" -d "$DB_NAME" < "$SRC_DIR/database.dump"
  echo "  Database restored successfully!"
fi

# 3. Restore uploads
if [ -f "$SRC_DIR/uploads.tar.gz" ]; then
  echo "→ Restoring user uploads..."
  if [ -d "backend/storage" ]; then
    rm -rf backend/storage/*
    tar -xzf "$SRC_DIR/uploads.tar.gz" -C backend
    echo "  User uploads restored to local folder!"
  elif docker volume inspect aevix_aevix_storage >/dev/null 2>&1; then
    # Clear and restore volume
    docker run --rm -v aevix_aevix_storage:/volume alpine sh -c "rm -rf /volume/*"
    docker run --rm -v aevix_aevix_storage:/volume -v "$SRC_DIR:/backup" alpine tar -xzf /backup/uploads.tar.gz -C /volume
    echo "  User uploads restored to named volume!"
  else
    echo "  Warning: No upload storage directory or volume found. Cannot restore uploads."
  fi
fi

# Clean up
rm -rf "$EXTRACT_DIR"
echo "Restore process completed successfully!"
