#!/bin/bash

# RAG Platform Production Restore System
# Handles restoration of all critical data and configurations

set -euo pipefail

# Configuration
BACKUP_BASE_DIR="/opt/backups/rag-platform"
ENCRYPTION_KEY_FILE="/opt/backups/encryption.key"
LOG_FILE="/var/log/rag-platform-restore.log"
TEMP_RESTORE_DIR="/tmp/rag-platform-restore"

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
    log "ERROR" "Restore failed at line $1"
    cleanup_temp_files
    exit 1
}

trap 'handle_error ${LINENO}' ERR

# Cleanup temporary files
cleanup_temp_files() {
    if [[ -d "$TEMP_RESTORE_DIR" ]]; then
        rm -rf "$TEMP_RESTORE_DIR"
        log "INFO" "Cleaned up temporary restore directory"
    fi
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_FILE

Restore RAG Platform from encrypted backup file.

OPTIONS:
    -h, --help              Show this help message
    -f, --force             Force restore without confirmation
    -p, --partial COMPONENT Restore only specific component
    -d, --dry-run           Show what would be restored without doing it
    -v, --verbose           Verbose output

COMPONENTS:
    databases               PostgreSQL databases
    redis                   Redis data
    clickhouse              ClickHouse data
    volumes                 Docker volumes
    configs                 Configuration files
    logs                    Application logs
    metrics                 Prometheus metrics

EXAMPLES:
    $0 /backups/20240119_120000.tar.gz.enc
    $0 --partial databases /backups/20240119_120000.tar.gz.enc
    $0 --dry-run /backups/20240119_120000.tar.gz.enc

EOF
}

# Parse command line arguments
parse_args() {
    FORCE=false
    PARTIAL=""
    DRY_RUN=false
    VERBOSE=false
    BACKUP_FILE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -p|--partial)
                PARTIAL="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                BACKUP_FILE="$1"
                shift
                ;;
        esac
    done
    
    if [[ -z "$BACKUP_FILE" ]]; then
        log "ERROR" "Backup file is required"
        usage
        exit 1
    fi
    
    if [[ ! -f "$BACKUP_FILE" ]]; then
        log "ERROR" "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
}

# Confirm restore operation
confirm_restore() {
    if [[ "$FORCE" == "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo "⚠️  WARNING: This will restore RAG Platform from backup and overwrite existing data!"
    echo "Backup file: $BACKUP_FILE"
    echo "Components to restore: ${PARTIAL:-all}"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log "INFO" "Restore cancelled by user"
        exit 0
    fi
}

# Decrypt and extract backup
decrypt_backup() {
    local backup_file="$1"
    log "INFO" "Decrypting and extracting backup"
    
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        log "ERROR" "Encryption key not found: $ENCRYPTION_KEY_FILE"
        exit 1
    fi
    
    # Create temporary directory
    mkdir -p "$TEMP_RESTORE_DIR"
    
    # Decrypt and extract
    openssl enc -aes-256-cbc -d -pbkdf2 -pass file:"$ENCRYPTION_KEY_FILE" -in "$backup_file" | \
        tar xzf - -C "$TEMP_RESTORE_DIR"
    
    # Find the extracted directory
    local extracted_dir=$(find "$TEMP_RESTORE_DIR" -maxdepth 1 -type d -name "2*" | head -1)
    if [[ -z "$extracted_dir" ]]; then
        log "ERROR" "Could not find extracted backup directory"
        exit 1
    fi
    
    echo "$extracted_dir"
}

# Stop services before restore
stop_services() {
    log "INFO" "Stopping RAG Platform services"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would stop Docker Compose services"
        return 0
    fi
    
    # Stop all services
    docker-compose -f infra/production/docker-compose.prod.yml down || true
    
    # Wait for containers to stop
    sleep 10
    
    log "INFO" "Services stopped"
}

# Start services after restore
start_services() {
    log "INFO" "Starting RAG Platform services"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would start Docker Compose services"
        return 0
    fi
    
    # Start core services first
    docker-compose -f infra/production/docker-compose.prod.yml up -d postgres redis clickhouse
    
    # Wait for databases to be ready
    sleep 30
    
    # Start remaining services
    docker-compose -f infra/production/docker-compose.prod.yml up -d
    
    log "INFO" "Services started"
}

# Restore PostgreSQL databases
restore_postgres() {
    local restore_dir="$1"
    log "INFO" "Restoring PostgreSQL databases"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would restore PostgreSQL databases from $restore_dir/databases/"
        return 0
    fi
    
    # Wait for PostgreSQL to be ready
    local retries=30
    while ! PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
        retries=$((retries - 1))
        if [[ $retries -eq 0 ]]; then
            log "ERROR" "PostgreSQL not ready after 30 attempts"
            exit 1
        fi
        sleep 1
    done
    
    # Restore global settings first
    if [[ -f "$restore_dir/databases/globals.sql.gz" ]]; then
        log "INFO" "Restoring PostgreSQL global settings"
        zcat "$restore_dir/databases/globals.sql.gz" | \
            PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres
    fi
    
    # Restore main database
    if [[ -f "$restore_dir/databases/rag_platform.sql.gz" ]]; then
        log "INFO" "Restoring main database: $POSTGRES_DB"
        
        # Drop and recreate database
        PGPASSWORD="$POSTGRES_PASSWORD" dropdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$POSTGRES_DB" --if-exists
        PGPASSWORD="$POSTGRES_PASSWORD" createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$POSTGRES_DB"
        
        # Restore data
        PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --verbose \
            --no-password \
            "$restore_dir/databases/rag_platform.sql.gz"
    fi
    
    # Restore Superset database
    if [[ -f "$restore_dir/databases/superset.sql.gz" ]]; then
        log "INFO" "Restoring Superset database: $SUPERSET_DB"
        
        PGPASSWORD="$POSTGRES_PASSWORD" dropdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$SUPERSET_DB" --if-exists
        PGPASSWORD="$POSTGRES_PASSWORD" createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$SUPERSET_DB"
        
        PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$SUPERSET_DB" \
            --verbose \
            --no-password \
            "$restore_dir/databases/superset.sql.gz"
    fi
    
    # Restore Grafana database
    if [[ -f "$restore_dir/databases/grafana.sql.gz" ]]; then
        log "INFO" "Restoring Grafana database: $GRAFANA_DB"
        
        PGPASSWORD="$POSTGRES_PASSWORD" dropdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$GRAFANA_DB" --if-exists
        PGPASSWORD="$POSTGRES_PASSWORD" createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$GRAFANA_DB"
        
        PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$GRAFANA_DB" \
            --verbose \
            --no-password \
            "$restore_dir/databases/grafana.sql.gz"
    fi
    
    log "INFO" "PostgreSQL restore completed"
}

# Restore Redis data
restore_redis() {
    local restore_dir="$1"
    log "INFO" "Restoring Redis data"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would restore Redis data from $restore_dir/databases/"
        return 0
    fi
    
    if [[ -f "$restore_dir/databases/redis-dump.rdb.gz" ]]; then
        # Stop Redis temporarily
        docker stop rag-platform-redis-prod || true
        
        # Extract and copy RDB file
        zcat "$restore_dir/databases/redis-dump.rdb.gz" > /tmp/dump.rdb
        docker cp /tmp/dump.rdb rag-platform-redis-prod:/data/dump.rdb
        rm /tmp/dump.rdb
        
        # Start Redis
        docker start rag-platform-redis-prod
        
        # Wait for Redis to be ready
        local retries=30
        while ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; do
            retries=$((retries - 1))
            if [[ $retries -eq 0 ]]; then
                log "ERROR" "Redis not ready after 30 attempts"
                exit 1
            fi
            sleep 1
        done
        
        log "INFO" "Redis restore completed"
    else
        log "WARNING" "Redis backup file not found"
    fi
}

# Restore ClickHouse data
restore_clickhouse() {
    local restore_dir="$1"
    log "INFO" "Restoring ClickHouse data"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would restore ClickHouse data from $restore_dir/databases/"
        return 0
    fi
    
    # Restore table data
    for file in "$restore_dir/databases/clickhouse-"*.tsv.gz; do
        if [[ -f "$file" ]]; then
            local table_name=$(basename "$file" .tsv.gz | sed 's/clickhouse-//')
            log "INFO" "Restoring ClickHouse table: $table_name"
            
            # Create table if needed and insert data
            zcat "$file" | docker exec -i rag-platform-clickhouse-prod clickhouse-client --query="INSERT INTO metrics.$table_name FORMAT TabSeparated"
        fi
    done
    
    log "INFO" "ClickHouse restore completed"
}

# Restore Docker volumes
restore_volumes() {
    local restore_dir="$1"
    log "INFO" "Restoring Docker volumes"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would restore Docker volumes from $restore_dir/volumes/"
        return 0
    fi
    
    # Stop all services first
    docker-compose -f infra/production/docker-compose.prod.yml down
    
    # Restore each volume
    for volume_file in "$restore_dir/volumes/"*.tar.gz; do
        if [[ -f "$volume_file" ]]; then
            local volume_name=$(basename "$volume_file" .tar.gz)
            log "INFO" "Restoring volume: $volume_name"
            
            # Remove existing volume
            docker volume rm "$volume_name" 2>/dev/null || true
            
            # Create new volume and restore data
            docker volume create "$volume_name"
            docker run --rm \
                -v "$volume_name":/volume \
                -v "$restore_dir/volumes":/backup:ro \
                alpine:latest \
                tar xzf "/backup/$(basename "$volume_file")" -C /volume
        fi
    done
    
    log "INFO" "Docker volumes restore completed"
}

# Restore configuration files
restore_configs() {
    local restore_dir="$1"
    log "INFO" "Restoring configuration files"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY RUN] Would restore configuration files from $restore_dir/configs/"
        return 0
    fi
    
    if [[ -d "$restore_dir/configs" ]]; then
        # Backup current configs
        if [[ -d "infra/production" ]]; then
            mv infra/production "infra/production.backup.$(date +%s)"
        fi
        
        # Restore configs
        cp -r "$restore_dir/configs/production" infra/
        cp "$restore_dir/configs/"docker-compose*.yml . 2>/dev/null || true
        cp "$restore_dir/configs/"*.env . 2>/dev/null || true
        
        # Restore system configs if running as root
        if [[ $EUID -eq 0 && -d "$restore_dir/configs/nginx" ]]; then
            cp -r "$restore_dir/configs/nginx" /etc/
        fi
        
        log "INFO" "Configuration files restore completed"
    else
        log "WARNING" "Configuration backup not found"
    fi
}

# Show restore summary
show_summary() {
    local restore_dir="$1"
    
    echo ""
    echo "📋 RESTORE SUMMARY"
    echo "=================="
    echo "Backup source: $BACKUP_FILE"
    echo "Restore directory: $restore_dir"
    echo "Components:"
    
    [[ -z "$PARTIAL" || "$PARTIAL" == "databases" ]] && [[ -d "$restore_dir/databases" ]] && echo "  ✅ Databases"
    [[ -z "$PARTIAL" || "$PARTIAL" == "redis" ]] && [[ -f "$restore_dir/databases/redis-dump.rdb.gz" ]] && echo "  ✅ Redis data"
    [[ -z "$PARTIAL" || "$PARTIAL" == "clickhouse" ]] && [[ -n "$(ls "$restore_dir/databases/clickhouse-"*.tsv.gz 2>/dev/null)" ]] && echo "  ✅ ClickHouse data"
    [[ -z "$PARTIAL" || "$PARTIAL" == "volumes" ]] && [[ -d "$restore_dir/volumes" ]] && echo "  ✅ Docker volumes"
    [[ -z "$PARTIAL" || "$PARTIAL" == "configs" ]] && [[ -d "$restore_dir/configs" ]] && echo "  ✅ Configuration files"
    [[ -z "$PARTIAL" || "$PARTIAL" == "logs" ]] && [[ -d "$restore_dir/logs" ]] && echo "  ✅ Application logs"
    [[ -z "$PARTIAL" || "$PARTIAL" == "metrics" ]] && [[ -d "$restore_dir/metrics" ]] && echo "  ✅ Metrics data"
    
    echo ""
}

# Main restore function
main() {
    parse_args "$@"
    
    log "INFO" "Starting RAG Platform restore process"
    log "INFO" "Backup file: $BACKUP_FILE"
    log "INFO" "Component filter: ${PARTIAL:-all}"
    log "INFO" "Dry run: $DRY_RUN"
    
    # Confirm operation
    confirm_restore
    
    # Decrypt and extract backup
    local restore_dir
    restore_dir=$(decrypt_backup "$BACKUP_FILE")
    
    # Show what will be restored
    show_summary "$restore_dir"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "Dry run completed - no changes made"
        cleanup_temp_files
        exit 0
    fi
    
    # Stop services
    stop_services
    
    # Perform restore based on components
    if [[ -z "$PARTIAL" || "$PARTIAL" == "volumes" ]]; then
        restore_volumes "$restore_dir"
    fi
    
    if [[ -z "$PARTIAL" || "$PARTIAL" == "configs" ]]; then
        restore_configs "$restore_dir"
    fi
    
    # Start core services
    start_services
    
    if [[ -z "$PARTIAL" || "$PARTIAL" == "databases" ]]; then
        restore_postgres "$restore_dir"
    fi
    
    if [[ -z "$PARTIAL" || "$PARTIAL" == "redis" ]]; then
        restore_redis "$restore_dir"
    fi
    
    if [[ -z "$PARTIAL" || "$PARTIAL" == "clickhouse" ]]; then
        restore_clickhouse "$restore_dir"
    fi
    
    # Cleanup
    cleanup_temp_files
    
    log "INFO" "Restore process completed successfully"
    echo ""
    echo "🎉 RAG Platform restore completed!"
    echo ""
    echo "Next steps:"
    echo "1. Verify all services are running: docker-compose ps"
    echo "2. Check application health: curl http://localhost/health"
    echo "3. Test login and basic functionality"
    echo "4. Review logs for any issues"
}

# Run restore if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
