#!/bin/bash

# Service management script - Start and monitor miroimage and miroshape services simultaneously
# Usage:
#   Start: ./servers/start_servers.sh start --miroimage-gpu 0 --miroshape-gpu 1
#   Stop: ./servers/start_servers.sh stop
#   Restart: ./servers/start_servers.sh restart --miroimage-gpu 0 --miroshape-gpu 1
#   Status: ./servers/start_servers.sh status
#   Logs: ./servers/start_servers.sh logs [miroimage|miroshape|all]
#   Monitor: ./servers/start_servers.sh monitor

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_DIR="${SCRIPT_DIR}/pids"

MIROIMAGE_LOG="${LOG_DIR}/miroimage.log"
MIROSHAPE_LOG="${LOG_DIR}/miroshape.log"
MIROIMAGE_PID="${PID_DIR}/miroimage.pid"
MIROSHAPE_PID="${PID_DIR}/miroshape.pid"

# Default configuration
DEFAULT_MIROIMAGE_GPU=0
DEFAULT_MIROSHAPE_GPU=0
DEFAULT_MIROIMAGE_HOST="0.0.0.0"
DEFAULT_MIROIMAGE_PORT=8081
DEFAULT_MIROIMAGE_MODEL_PATH="Qwen/Qwen-Image-Edit-2511"
DEFAULT_MIROIMAGE_MODEL_NAME="Qwen-Image-Edit-2511"
DEFAULT_MIROSHAPE_MODEL_PATH="IntimeAI/Miro"
DEFAULT_MIROSHAPE_OUTPUT_DIR="./output/output_shape"
DEFAULT_MIROSHAPE_HOST="0.0.0.0"
DEFAULT_MIROSHAPE_PORT=8080

# Fixed parameters (not exposed as CLI options)
MIROIMAGE_NUM_INFERENCE_STEPS=50
MIROIMAGE_CFG_SCALE=4.0
MIROIMAGE_GUIDANCE_SCALE=1.0
MIROIMAGE_LAYERS=4
MIROIMAGE_RESOLUTION=640

# Create necessary directories
mkdir -p "${LOG_DIR}"
mkdir -p "${PID_DIR}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Parse command line arguments
parse_args() {
    MIROIMAGE_GPU=$DEFAULT_MIROIMAGE_GPU
    MIROSHAPE_GPU=$DEFAULT_MIROSHAPE_GPU
    MIROIMAGE_HOST=$DEFAULT_MIROIMAGE_HOST
    MIROIMAGE_PORT=$DEFAULT_MIROIMAGE_PORT
    MIROIMAGE_MODEL_PATH=$DEFAULT_MIROIMAGE_MODEL_PATH
    MIROIMAGE_MODEL_NAME=$DEFAULT_MIROIMAGE_MODEL_NAME
    MIROSHAPE_MODEL_PATH=$DEFAULT_MIROSHAPE_MODEL_PATH
    MIROSHAPE_OUTPUT_DIR=$DEFAULT_MIROSHAPE_OUTPUT_DIR
    MIROSHAPE_HOST=$DEFAULT_MIROSHAPE_HOST
    MIROSHAPE_PORT=$DEFAULT_MIROSHAPE_PORT
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --miroimage-gpu)
                MIROIMAGE_GPU="$2"
                shift 2
                ;;
            --miroshape-gpu)
                MIROSHAPE_GPU="$2"
                shift 2
                ;;
            --miroimage-host)
                MIROIMAGE_HOST="$2"
                shift 2
                ;;
            --miroimage-port)
                MIROIMAGE_PORT="$2"
                shift 2
                ;;
            --miroimage-model-path)
                MIROIMAGE_MODEL_PATH="$2"
                shift 2
                ;;
            --miroimage-model-name)
                MIROIMAGE_MODEL_NAME="$2"
                shift 2
                ;;
            --miroshape-model-path)
                MIROSHAPE_MODEL_PATH="$2"
                shift 2
                ;;
            --miroshape-output-dir)
                MIROSHAPE_OUTPUT_DIR="$2"
                shift 2
                ;;
            --miroshape-host)
                MIROSHAPE_HOST="$2"
                shift 2
                ;;
            --miroshape-port)
                MIROSHAPE_PORT="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
}

# Start miroimage service
start_miroimage() {
    if is_running "$MIROIMAGE_PID"; then
        log_warning "MiroImage service is already running (PID: $(cat $MIROIMAGE_PID))"
        return 1
    fi
    
    log_info "Starting MiroImage service (GPU: $MIROIMAGE_GPU, Port: $MIROIMAGE_PORT)..."
    
    CUDA_VISIBLE_DEVICES=$MIROIMAGE_GPU \
    MIROIMAGE_HOST=$MIROIMAGE_HOST \
    MIROIMAGE_PORT=$MIROIMAGE_PORT \
    MIROIMAGE_MODEL_PATH=$MIROIMAGE_MODEL_PATH \
    MIROIMAGE_MODEL_NAME=$MIROIMAGE_MODEL_NAME \
    MIROIMAGE_NUM_INFERENCE_STEPS=$MIROIMAGE_NUM_INFERENCE_STEPS \
    MIROIMAGE_CFG_SCALE=$MIROIMAGE_CFG_SCALE \
    MIROIMAGE_GUIDANCE_SCALE=$MIROIMAGE_GUIDANCE_SCALE \
    MIROIMAGE_LAYERS=$MIROIMAGE_LAYERS \
    MIROIMAGE_RESOLUTION=$MIROIMAGE_RESOLUTION \
    python3 "${SCRIPT_DIR}/miroimage_server.py" > "$MIROIMAGE_LOG" 2>&1 &
    
    local pid=$!
    echo $pid > "$MIROIMAGE_PID"
    
    # Wait for service to start
    sleep 2
    
    if is_running "$MIROIMAGE_PID"; then
        log_success "MiroImage service started successfully (PID: $pid, GPU: $MIROIMAGE_GPU, Port: $MIROIMAGE_PORT)"
        return 0
    else
        log_error "MiroImage service failed to start, check log: $MIROIMAGE_LOG"
        rm -f "$MIROIMAGE_PID"
        return 1
    fi
}

# Start miroshape service
start_miroshape() {
    if is_running "$MIROSHAPE_PID"; then
        log_warning "MiroShape service is already running (PID: $(cat $MIROSHAPE_PID))"
        return 1
    fi
    
    log_info "Starting MiroShape service (GPU: $MIROSHAPE_GPU, Port: $MIROSHAPE_PORT)..."
    
    CUDA_VISIBLE_DEVICES=$MIROSHAPE_GPU \
    MIROSHAPE_MODEL_PATH=$MIROSHAPE_MODEL_PATH \
    MIROSHAPE_OUTPUT_DIR=$MIROSHAPE_OUTPUT_DIR \
    MIROSHAPE_HOST=$MIROSHAPE_HOST \
    MIROSHAPE_PORT=$MIROSHAPE_PORT \
    python3 "${SCRIPT_DIR}/miroshape_server.py" > "$MIROSHAPE_LOG" 2>&1 &
    
    local pid=$!
    echo $pid > "$MIROSHAPE_PID"
    
    # Wait for service to start
    sleep 2
    
    if is_running "$MIROSHAPE_PID"; then
        log_success "MiroShape service started successfully (PID: $pid, GPU: $MIROSHAPE_GPU, Port: $MIROSHAPE_PORT)"
        return 0
    else
        log_error "MiroShape service failed to start, check log: $MIROSHAPE_LOG"
        rm -f "$MIROSHAPE_PID"
        return 1
    fi
}

# Stop service
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if ! is_running "$pid_file"; then
        log_warning "$service_name service is not running"
        return 1
    fi
    
    local pid=$(cat "$pid_file")
    log_info "Stopping $service_name service (PID: $pid)..."
    
    kill $pid
    
    # Wait for process to terminate
    local count=0
    while ps -p $pid > /dev/null 2>&1 && [ $count -lt 30 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    if ps -p $pid > /dev/null 2>&1; then
        log_warning "Process not responding, force killing..."
        kill -9 $pid
        sleep 1
    fi
    
    rm -f "$pid_file"
    log_success "$service_name service stopped"
}

# Show service status
show_status() {
    echo "========================================"
    echo "Service Status"
    echo "========================================"
    
    # MiroImage status
    echo -n "MiroImage Service: "
    if is_running "$MIROIMAGE_PID"; then
        local pid=$(cat "$MIROIMAGE_PID")
        echo -e "${GREEN}Running${NC} (PID: $pid)"
        echo "  Log: $MIROIMAGE_LOG"
    else
        echo -e "${RED}Not Running${NC}"
    fi
    
    echo ""
    
    # MiroShape status
    echo -n "MiroShape Service: "
    if is_running "$MIROSHAPE_PID"; then
        local pid=$(cat "$MIROSHAPE_PID")
        echo -e "${GREEN}Running${NC} (PID: $pid)"
        echo "  Log: $MIROSHAPE_LOG"
    else
        echo -e "${RED}Not Running${NC}"
    fi
    
    echo "========================================"
}

# Show logs
show_logs() {
    local service=${1:-all}
    local lines=${2:-50}
    
    case $service in
        miroimage)
            log_info "MiroImage last $lines lines of log:"
            echo "----------------------------------------"
            tail -n $lines "$MIROIMAGE_LOG" 2>/dev/null || echo "Log file does not exist"
            ;;
        miroshape)
            log_info "MiroShape last $lines lines of log:"
            echo "----------------------------------------"
            tail -n $lines "$MIROSHAPE_LOG" 2>/dev/null || echo "Log file does not exist"
            ;;
        all)
            log_info "MiroImage last $lines lines of log:"
            echo "----------------------------------------"
            tail -n $lines "$MIROIMAGE_LOG" 2>/dev/null || echo "Log file does not exist"
            echo ""
            log_info "MiroShape last $lines lines of log:"
            echo "----------------------------------------"
            tail -n $lines "$MIROSHAPE_LOG" 2>/dev/null || echo "Log file does not exist"
            ;;
        *)
            log_error "Unknown service: $service (options: miroimage, miroshape, all)"
            return 1
            ;;
    esac
}

# Monitor services (continuous monitoring mode)
monitor_services() {
    log_info "Starting service monitoring (Press Ctrl+C to exit)..."
    echo ""
    
    while true; do
        clear
        show_status
        
        echo ""
        echo "Recent log updates:"
        echo "----------------------------------------"
        
        if is_running "$MIROIMAGE_PID"; then
            echo -e "${BLUE}[MiroImage]${NC}"
            tail -n 3 "$MIROIMAGE_LOG" 2>/dev/null | sed 's/^/  /'
        fi
        
        echo ""
        
        if is_running "$MIROSHAPE_PID"; then
            echo -e "${BLUE}[MiroShape]${NC}"
            tail -n 3 "$MIROSHAPE_LOG" 2>/dev/null | sed 's/^/  /'
        fi
        
        echo ""
        echo "Next update in 5 seconds..."
        sleep 5
    done
}

# Show help
show_help() {
    cat << EOF
Service Management Script - Start and monitor MiroImage and MiroShape services

Usage:
  $0 <command> [options]

Commands:
  start      Start all services
  stop       Stop all services
  restart    Restart all services
  status     Show service status
  logs       Show service logs [miroimage|miroshape|all] [lines]
  monitor    Continuously monitor service status
  help       Show this help message

Options:
  --miroimage-gpu <gpu_id>              GPU device for MiroImage (default: $DEFAULT_MIROIMAGE_GPU)
  --miroshape-gpu <gpu_id>              GPU device for MiroShape (default: $DEFAULT_MIROSHAPE_GPU)
  --miroimage-host <host>               Host for MiroImage (default: $DEFAULT_MIROIMAGE_HOST)
  --miroimage-port <port>               Port for MiroImage (default: $DEFAULT_MIROIMAGE_PORT)
  --miroimage-model-path <path>         Model path for MiroImage (default: $DEFAULT_MIROIMAGE_MODEL_PATH)
  --miroimage-model-name <name>         Model name for MiroImage (default: $DEFAULT_MIROIMAGE_MODEL_NAME)
  --miroshape-model-path <path>         Model path for MiroShape (default: $DEFAULT_MIROSHAPE_MODEL_PATH)
  --miroshape-output-dir <dir>          Output directory for MiroShape (default: $DEFAULT_MIROSHAPE_OUTPUT_DIR)
  --miroshape-host <host>               Host for MiroShape (default: $DEFAULT_MIROSHAPE_HOST)
  --miroshape-port <port>               Port for MiroShape (default: $DEFAULT_MIROSHAPE_PORT)

Examples:
  # Start with default settings
  $0 start

  # Start with custom GPU assignment
  $0 start --miroimage-gpu 0 --miroshape-gpu 1

  # Start with custom ports
  $0 start --miroimage-port 8081 --miroshape-port 8082

  # Start with custom model paths
  $0 start --miroimage-model-path /path/to/model --miroshape-model-path /path/to/model

  # Stop all services
  $0 stop

  # Restart with custom settings
  $0 restart --miroimage-gpu 2 --miroshape-gpu 3

  # Show status
  $0 status

  # View logs
  $0 logs miroimage 100
  $0 logs all

  # Monitor services
  $0 monitor

Directories:
  Log directory: $LOG_DIR
  PID directory: $PID_DIR

EOF
}

# Main function
main() {
    local command=${1:-help}
    shift || true
    
    case $command in
        start)
            parse_args "$@"
            log_info "Starting all services..."
            start_miroimage
            start_miroshape
            echo ""
            show_status
            ;;
            
        stop)
            log_info "Stopping all services..."
            stop_service "MiroImage" "$MIROIMAGE_PID"
            stop_service "MiroShape" "$MIROSHAPE_PID"
            ;;
            
        restart)
            parse_args "$@"
            log_info "Restarting all services..."
            stop_service "MiroImage" "$MIROIMAGE_PID"
            stop_service "MiroShape" "$MIROSHAPE_PID"
            sleep 2
            start_miroimage
            start_miroshape
            echo ""
            show_status
            ;;
            
        status)
            show_status
            ;;
            
        logs)
            show_logs ${1:-all} ${2:-50}
            ;;
            
        monitor)
            monitor_services
            ;;
            
        help|--help|-h)
            show_help
            ;;
            
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
