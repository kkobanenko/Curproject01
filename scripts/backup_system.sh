#!/bin/bash

# RAG Platform Production Backup System
# Handles backup of all critical data and configurations

set -euo pipefail

# Configuration
BACKUP_BASE_DIR="/opt/backups/rag-platform"
RETENTION_DAYS=30
ENCRYPTION_KEY_FILE="/opt/backups/encryption.key"
NOTIFICATION_WEBHOOK="${BACKUP_NOTIFICATION_WEBHOOK:-}"
LOG_FILE="/var/log/rag-platform-backup.log"

# Database configurations
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-rag_platform}"
SUPERSET_DB="${SUPERSET_DB:-superset}"
GRAFANA_DB="${GRAFANA_DB:-grafana}"

# Services
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-localhost}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT:-8123}"

# Logging function
log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    log "ERROR" "Backup failed at line $1"
    send_notification "❌ RAG Platform Backup Failed" "Backup process failed at line $1. Check logs for details."
    exit 1
}

trap 'handle_error ${LINENO}' ERR

# Notification function
send_notification() {
    local title="$1"
    local message="$2"
    
    if [[ -n "$NOTIFICATION_WEBHOOK" ]]; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"title\": \"$title\", \"message\": \"$message\"}" \
            --max-time 30 --silent || true
    fi
    
    log "INFO" "Notification: $title - $message"
}

# Create backup directory structure
create_backup_dirs() {
    local backup_date="$1"
    local backup_dir="$BACKUP_BASE_DIR/$backup_date"
    
    mkdir -p "$backup_dir"/{databases,volumes,configs,logs,metrics}
    echo "$backup_dir"
}

# Backup PostgreSQL databases
backup_postgres() {
    local backup_dir="$1"
    log "INFO" "Starting PostgreSQL backup"
    
    # Main RAG platform database
    log "INFO" "Backing up main database: $POSTGRES_DB"
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$backup_dir/databases/rag_platform.sql.gz"
    
    # Superset database
    log "INFO" "Backing up Superset database: $SUPERSET_DB"
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$SUPERSET_DB" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$backup_dir/databases/superset.sql.gz"
    
    # Grafana database
    log "INFO" "Backing up Grafana database: $GRAFANA_DB"
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$GRAFANA_DB" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$backup_dir/databases/grafana.sql.gz"
    
    # Database schema and metadata
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dumpall \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        --globals-only \
        --verbose \
        --no-password | gzip > "$backup_dir/databases/globals.sql.gz"
    
    log "INFO" "PostgreSQL backup completed"
}

# Backup Redis data
backup_redis() {
    local backup_dir="$1"
    log "INFO" "Starting Redis backup"
    
    # Trigger Redis BGSAVE
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE
    
    # Wait for background save to complete
    while [[ $(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE) == $(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE) ]]; do
        sleep 1
    done
    
    # Copy the RDB file
    docker cp rag-platform-redis-prod:/data/dump.rdb "$backup_dir/databases/redis-dump.rdb"
    gzip "$backup_dir/databases/redis-dump.rdb"
    
    log "INFO" "Redis backup completed"
}

# Backup ClickHouse data
backup_clickhouse() {
    local backup_dir="$1"
    log "INFO" "Starting ClickHouse backup"
    
    # Create ClickHouse backup using clickhouse-backup tool or manual export
    docker exec rag-platform-clickhouse-prod clickhouse-client --query="BACKUP DATABASE metrics TO Disk('default', '$backup_dir/databases/clickhouse-backup')"
    
    # Alternative: Export tables manually
    docker exec rag-platform-clickhouse-prod clickhouse-client --query="SHOW TABLES FROM metrics" | while read table; do
        docker exec rag-platform-clickhouse-prod clickhouse-client --query="SELECT * FROM metrics.$table FORMAT TabSeparated" | gzip > "$backup_dir/databases/clickhouse-$table.tsv.gz"
    done
    
    log "INFO" "ClickHouse backup completed"
}

# Backup Docker volumes
backup_volumes() {
    local backup_dir="$1"
    log "INFO" "Starting Docker volumes backup"
    
    # List of critical volumes to backup
    local volumes=(
        "postgres_data_prod"
        "redis_data_prod" 
        "clickhouse_data_prod"
        "ollama_data_prod"
        "superset_data_prod"
        "grafana_data_prod"
        "prometheus_data_prod"
        "documents_data_prod"
    )
    
    for volume in "${volumes[@]}"; do
        log "INFO" "Backing up volume: $volume"
        
        # Create tar archive of volume data
        docker run --rm \
            -v "$volume":/volume:ro \
            -v "$backup_dir/volumes":/backup \
            alpine:latest \
            tar czf "/backup/$volume.tar.gz" -C /volume .
    done
    
    log "INFO" "Docker volumes backup completed"
}

# Backup configuration files
backup_configs() {
    local backup_dir="$1"
    log "INFO" "Starting configuration backup"
    
    # Copy critical configuration files
    cp -r infra/production "$backup_dir/configs/"
    cp -r .env* "$backup_dir/configs/" 2>/dev/null || true
    cp -r scripts "$backup_dir/configs/"
    cp docker-compose*.yml "$backup_dir/configs/" 2>/dev/null || true
    
    # Backup Nginx configurations
    if [[ -d "/etc/nginx" ]]; then
        cp -r /etc/nginx "$backup_dir/configs/"
    fi
    
    # Backup SSL certificates (if any)
    if [[ -d "/etc/ssl/certs" ]]; then
        cp -r /etc/ssl/certs "$backup_dir/configs/"
    fi
    
    log "INFO" "Configuration backup completed"
}

# Backup application logs
backup_logs() {
    local backup_dir="$1"
    log "INFO" "Starting logs backup"
    
    # Docker container logs
    docker ps --format "table {{.Names}}" | grep -E "rag-platform" | while read container; do
        docker logs "$container" 2>&1 | gzip > "$backup_dir/logs/$container.log.gz"
    done
    
    # System logs
    if [[ -f "/var/log/nginx/access.log" ]]; then
        cp /var/log/nginx/access.log "$backup_dir/logs/"
        gzip "$backup_dir/logs/access.log"
    fi
    
    if [[ -f "/var/log/nginx/error.log" ]]; then
        cp /var/log/nginx/error.log "$backup_dir/logs/"
        gzip "$backup_dir/logs/error.log"
    fi
    
    log "INFO" "Logs backup completed"
}

# Export Prometheus metrics for historical analysis
backup_metrics() {
    local backup_dir="$1"
    log "INFO" "Starting metrics backup"
    
    # Export key metrics from the last 7 days
    local end_time=$(date +%s)
    local start_time=$((end_time - 604800))  # 7 days ago
    
    local metrics=(
        "up"
        "http_requests_total"
        "http_request_duration_seconds"
        "node_cpu_seconds_total"
        "node_memory_MemAvailable_bytes"
        "rag_queries_total"
        "document_processing_duration_seconds"
    )
    
    for metric in "${metrics[@]}"; do
        curl -s "http://localhost:9090/api/v1/query_range?query=$metric&start=$start_time&end=$end_time&step=300" | \
            jq . > "$backup_dir/metrics/$metric.json"
    done
    
    log "INFO" "Metrics backup completed"
}

# Encrypt backup directory
encrypt_backup() {
    local backup_dir="$1"
    log "INFO" "Starting backup encryption"
    
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        log "WARNING" "Encryption key not found, generating new key"
        openssl rand -base64 32 > "$ENCRYPTION_KEY_FILE"
        chmod 600 "$ENCRYPTION_KEY_FILE"
    fi
    
    # Create encrypted tar archive
    local encrypted_file="$backup_dir.tar.gz.enc"
    tar czf - -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")" | \
        openssl enc -aes-256-cbc -salt -pbkdf2 -pass file:"$ENCRYPTION_KEY_FILE" > "$encrypted_file"
    
    # Remove unencrypted backup
    rm -rf "$backup_dir"
    
    log "INFO" "Backup encryption completed: $encrypted_file"
    echo "$encrypted_file"
}

# Upload to remote storage (S3, etc.)
upload_backup() {
    local backup_file="$1"
    
    if [[ -n "${AWS_S3_BUCKET:-}" ]]; then
        log "INFO" "Uploading backup to S3"
        aws s3 cp "$backup_file" "s3://$AWS_S3_BUCKET/rag-platform-backups/"
        log "INFO" "S3 upload completed"
    fi
    
    if [[ -n "${RSYNC_DESTINATION:-}" ]]; then
        log "INFO" "Uploading backup via rsync"
        rsync -avz "$backup_file" "$RSYNC_DESTINATION"
        log "INFO" "Rsync upload completed"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "INFO" "Cleaning up old backups (retention: $RETENTION_DAYS days)"
    find "$BACKUP_BASE_DIR" -name "*.tar.gz.enc" -mtime +$RETENTION_DAYS -delete
    log "INFO" "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    log "INFO" "Verifying backup integrity"
    
    # Test encrypted file can be decrypted
    openssl enc -aes-256-cbc -d -pbkdf2 -pass file:"$ENCRYPTION_KEY_FILE" -in "$backup_file" | tar tzf - > /dev/null
    
    local file_size=$(stat -c%s "$backup_file")
    log "INFO" "Backup verification passed. File size: $(numfmt --to=iec $file_size)"
}

# Generate backup report
generate_report() {
    local backup_file="$1"
    local backup_size=$(stat -c%s "$backup_file")
    local backup_date=$(date)
    
    local report_file="$BACKUP_BASE_DIR/backup-report-$(date +%Y%m%d).txt"
    
    cat > "$report_file" << EOF
RAG Platform Backup Report
==========================

Backup Date: $backup_date
Backup File: $(basename "$backup_file")
Backup Size: $(numfmt --to=iec $backup_size)
Retention Policy: $RETENTION_DAYS days

Components Backed Up:
- PostgreSQL databases (main, superset, grafana)
- Redis data
- ClickHouse metrics
- Docker volumes
- Configuration files
- Application logs
- Prometheus metrics (7 days)

Backup Status: SUCCESS
Encryption: AES-256-CBC
Verification: PASSED

Next Backup: $(date -d '+1 day')
EOF

    log "INFO" "Backup report generated: $report_file"
}

# Main backup function
main() {
    log "INFO" "Starting RAG Platform backup process"
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir
    
    # Check prerequisites
    command -v docker >/dev/null 2>&1 || { log "ERROR" "Docker not found"; exit 1; }
    command -v pg_dump >/dev/null 2>&1 || { log "ERROR" "pg_dump not found"; exit 1; }
    command -v redis-cli >/dev/null 2>&1 || { log "ERROR" "redis-cli not found"; exit 1; }
    
    # Create backup directory
    backup_dir=$(create_backup_dirs "$backup_date")
    
    # Perform backups
    backup_postgres "$backup_dir"
    backup_redis "$backup_dir"
    backup_clickhouse "$backup_dir"
    backup_volumes "$backup_dir"
    backup_configs "$backup_dir"
    backup_logs "$backup_dir"
    backup_metrics "$backup_dir"
    
    # Encrypt backup
    local encrypted_file
    encrypted_file=$(encrypt_backup "$backup_dir")
    
    # Verify backup
    verify_backup "$encrypted_file"
    
    # Upload to remote storage
    upload_backup "$encrypted_file"
    
    # Generate report
    generate_report "$encrypted_file"
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "INFO" "Backup process completed successfully"
    send_notification "✅ RAG Platform Backup Complete" "Backup completed successfully. File: $(basename "$encrypted_file")"
}

# Run backup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
