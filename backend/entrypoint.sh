#!/bin/sh
set -e

echo "=== Aevix Production Bootloader ==="

# 1. Wait for database connection using a Python one-liner socket check
python -c "
import socket
import time
import os
import sys

db_url = os.environ.get('DATABASE_URL', '')
if 'sqlite' in db_url:
    print('SQLite database detected. Skipping database connection check.')
    sys.exit(0)

try:
    host_port = db_url.split('@')[1].split('/')[0]
    if ':' in host_port:
        host, port = host_port.split(':')
        port = int(port)
    else:
        host, port = host_port, 5432
except Exception:
    host = 'postgres'
    port = 5432

print(f'Waiting for PostgreSQL database to start at {host}:{port}...')
start_time = time.time()
while True:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        s.close()
        print('PostgreSQL database is available!')
        break
    except socket.error:
        if time.time() - start_time > 60:
            print('Error: Timeout waiting for PostgreSQL database')
            sys.exit(1)
        time.sleep(1)
"

# 2. Run Database Migrations using Alembic (if not running a simple worker or if it's the web container)
# We execute migrations on start.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Database migrations completed successfully!"

    # 3. Verify pgvector extension
    echo "Verifying pgvector database extension..."
    python -c "
import asyncio
import sys
try:
    from app.database import engine
    from sqlalchemy import text
    async def check():
        async with engine.connect() as conn:
            res = await conn.execute(text(\"SELECT 1 FROM pg_extension WHERE extname = 'vector'\"))
            if res.scalar() is None:
                print('WARNING: pgvector extension is not registered in this database!')
                print('Running CREATE EXTENSION IF NOT EXISTS vector...')
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
                print('pgvector extension created successfully!')
            else:
                print('pgvector extension is loaded and active!')
    asyncio.run(check())
except Exception as e:
    print(f'Warning: Could not verify pgvector extension: {e}')
"
fi

# 4. Execute the main container command
echo "Bootloader finished. Running command: $@"
exec "$@"
