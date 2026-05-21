#!/bin/bash

# Sieve Kubernetes Cleanup Script
# This script removes all Sieve resources from Kubernetes cluster

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_warning() {
    echo -e "${RED}⚠ $1${NC}"
}

# Confirm deletion
confirm_deletion() {
    print_warning "This will DELETE all Sieve resources from Kubernetes!"
    print_warning "This includes:"
    echo "  - All deployments and pods"
    echo "  - All services"
    echo "  - All persistent volumes (DATABASE DATA WILL BE LOST!)"
    echo "  - All ConfigMaps and Secrets"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        print_info "Cleanup cancelled"
        exit 0
    fi
}

# Delete application services
delete_services() {
    print_info "Deleting application services..."
    kubectl delete -f api-gateway/ --ignore-not-found=true
    kubectl delete -f text-extractor/ --ignore-not-found=true
    kubectl delete -f media-extractor/ --ignore-not-found=true
    kubectl delete -f cron-notifier/ --ignore-not-found=true
    print_success "Application services deleted"
}

# Delete monitoring
delete_monitoring() {
    print_info "Deleting monitoring..."
    kubectl delete -f monitoring/ --ignore-not-found=true
    print_success "Monitoring deleted"
}

# Delete infrastructure
delete_infrastructure() {
    print_info "Deleting infrastructure..."
    kubectl delete -f postgres/ --ignore-not-found=true
    kubectl delete -f redis/ --ignore-not-found=true
    kubectl delete -f rabbitmq/ --ignore-not-found=true
    print_success "Infrastructure deleted"
}

# Delete ConfigMaps
delete_configmaps() {
    print_info "Deleting ConfigMaps..."
    kubectl delete configmap --all -n sieve --ignore-not-found=true
    print_success "ConfigMaps deleted"
}

# Delete Secrets
delete_secrets() {
    print_info "Deleting Secrets..."
    kubectl delete secret --all -n sieve --ignore-not-found=true
    print_success "Secrets deleted"
}

# Delete PVCs
delete_pvcs() {
    print_warning "Deleting Persistent Volume Claims (DATA WILL BE LOST!)..."
    kubectl delete pvc --all -n sieve --ignore-not-found=true
    print_success "PVCs deleted"
}

# Delete namespace
delete_namespace() {
    print_info "Deleting namespace..."
    kubectl delete namespace sieve --ignore-not-found=true
    print_success "Namespace deleted"
}

# Main cleanup
main() {
    echo "========================================="
    echo "  Sieve Kubernetes Cleanup"
    echo "========================================="
    echo ""
    
    confirm_deletion
    
    echo ""
    print_info "Starting cleanup..."
    echo ""
    
    delete_services
    delete_monitoring
    delete_infrastructure
    delete_configmaps
    delete_secrets
    delete_pvcs
    delete_namespace
    
    echo ""
    print_success "Cleanup completed!"
    echo ""
    print_info "All Sieve resources have been removed from Kubernetes"
}

# Run main
main
