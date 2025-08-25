#!/bin/bash
# Supervisor Control Script for Cage Container
# This script provides easy access to supervisor commands within the container

set -euo pipefail

SUPERVISOR_SOCKET="/tmp/supervisor.sock"
SUPERVISOR_CTL="/app/venv/bin/supervisorctl"

# Check if supervisor is running
check_supervisor() {
    if [ ! -S "$SUPERVISOR_SOCKET" ]; then
        echo "Error: Supervisor is not running (socket not found)"
        exit 1
    fi
}

# Show status of all processes
status() {
    echo "=== Supervisor Status ==="
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf status
}

# Start a specific process
start_process() {
    local process_name="$1"
    echo "Starting process: $process_name"
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf start "$process_name"
}

# Stop a specific process
stop_process() {
    local process_name="$1"
    echo "Stopping process: $process_name"
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf stop "$process_name"
}

# Restart a specific process
restart_process() {
    local process_name="$1"
    echo "Restarting process: $process_name"
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf restart "$process_name"
}

# Start all processes
start_all() {
    echo "Starting all processes..."
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf start all
}

# Stop all processes
stop_all() {
    echo "Stopping all processes..."
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf stop all
}

# Restart all processes
restart_all() {
    echo "Restarting all processes..."
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf restart all
}

# Show logs for a specific process
show_logs() {
    local process_name="$1"
    echo "=== Logs for $process_name ==="
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf tail "$process_name"
}

# Show error logs for a specific process
show_error_logs() {
    local process_name="$1"
    echo "=== Error logs for $process_name ==="
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf tail "$process_name" stderr
}

# Reload supervisor configuration
reload() {
    echo "Reloading supervisor configuration..."
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf reread
    $SUPERVISOR_CTL -c /etc/supervisor/conf.d/supervisord.conf update
}

# Show help
show_help() {
    cat << EOF
Supervisor Control Script for Cage Container

Usage: $0 <command> [process_name]

Commands:
    status                    Show status of all processes
    start <process>          Start a specific process
    stop <process>           Stop a specific process
    restart <process>        Restart a specific process
    start-all                Start all processes
    stop-all                 Stop all processes
    restart-all              Restart all processes
    logs <process>           Show logs for a specific process
    error-logs <process>     Show error logs for a specific process
    reload                   Reload supervisor configuration
    help                     Show this help message

Available Processes:
    checker-agent            CrewAI checker agent (runs every 10 minutes)
    agent-daemon             Main agent daemon process

Examples:
    $0 status
    $0 start checker-agent
    $0 logs checker-agent
    $0 restart-all

EOF
}

# Main script logic
main() {
    check_supervisor
    
    case "${1:-help}" in
        status)
            status
            ;;
        start)
            if [ -z "${2:-}" ]; then
                echo "Error: Process name required for start command"
                exit 1
            fi
            start_process "$2"
            ;;
        stop)
            if [ -z "${2:-}" ]; then
                echo "Error: Process name required for stop command"
                exit 1
            fi
            stop_process "$2"
            ;;
        restart)
            if [ -z "${2:-}" ]; then
                echo "Error: Process name required for restart command"
                exit 1
            fi
            restart_process "$2"
            ;;
        start-all)
            start_all
            ;;
        stop-all)
            stop_all
            ;;
        restart-all)
            restart_all
            ;;
        logs)
            if [ -z "${2:-}" ]; then
                echo "Error: Process name required for logs command"
                exit 1
            fi
            show_logs "$2"
            ;;
        error-logs)
            if [ -z "${2:-}" ]; then
                echo "Error: Process name required for error-logs command"
                exit 1
            fi
            show_error_logs "$2"
            ;;
        reload)
            reload
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
