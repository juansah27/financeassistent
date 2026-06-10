#!/bin/bash
# Script Backup Hermes Financial Strategist
BACKUP_DIR="/mnt/d/Project/financeassistent/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting backup to $BACKUP_DIR..."

# 1. Backup Database
echo "Dumping database..."
docker exec finance_db pg_dump -U finance_user -d finance_db > "$BACKUP_DIR/finance_db_dump_$TIMESTAMP.sql"

# 2. Backup Configs
echo "Copying config files..."
cp /home/ladyqiu/.hermes/config.yaml "$BACKUP_DIR/"
cp /home/ladyqiu/.hermes/.env "$BACKUP_DIR/"
cp /home/ladyqiu/.hermes/SOUL.md "$BACKUP_DIR/"
cp /home/ladyqiu/.hermes/AGENTS.md "$BACKUP_DIR/"
cp /home/ladyqiu/.hermes/state.db "$BACKUP_DIR/"

# 3. Backup Memories
echo "Copying memories..."
cp -r /home/ladyqiu/.hermes/memories "$BACKUP_DIR/"

echo "Backup completed successfully!"
ls -lh "$BACKUP_DIR"
