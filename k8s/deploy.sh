#!/bin/bash

# Sieve Kubernetes Deployment Script
# This script deploys Sieve to a Kubernetes cluster

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

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl first."
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please configure kubectl."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Create namespace
create_namespace() {
    print_info "Creating namespace..."
    kubectl apply -f namespace.yaml
    kubectl config set-context --current --namespace=sieve
    print_success "Namespace created"
}

# Create secrets
create_secrets() {
    print_info "Creating secrets..."
    
    # Check if secrets already exist
    if kubectl get secret sieve-secrets &> /dev/null; then
        print_info "Secrets already exist. Skipping..."
        return
    fi
    
    # Prompt for secrets
    read -p "Enter Telegram Bot Token: " TELEGRAM_BOT_TOKEN
    read -p "Enter Groq API Key: " GROQ_API_KEY
    read -p "Enter Google API Key: " GOOGLE_API_KEY
    
    kubectl create secret generic sieve-secrets \
        --from-literal=telegram-bot-token="$TELEGRAM_BOT_TOKEN" \
        --from-literal=groq-api-key="$GROQ_API_KEY" \
        --from-literal=google-api-key="$GOOGLE_API_KEY" \
        --namespace=sieve
    
    print_success "Secrets created"
}

# Apply ConfigMaps
apply_configmaps() {
    print_info "Applying ConfigMaps..."
    kubectl apply -f configmap.yaml
    kubectl apply -f postgres/configmap.yaml
    kubectl apply -f monitoring/prometheus-configmap.yaml
    kubectl apply -f monitoring/grafana-configmap.yaml
    kubectl apply -f monitoring/grafana-dashboard-provider.yaml
    kubectl apply -f monitoring/grafana-dashboards-configmap.yaml
    print_success "ConfigMaps applied"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_info "Deploying infrastructure (PostgreSQL, Redis, RabbitMQ)..."
    
    kubectl apply -f postgres/
    kubectl apply -f redis/
    kubectl apply -f rabbitmq/
    
    print_info "Waiting for infrastructure to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s || true
    kubectl wait --for=condition=ready pod -l app=redis --timeout=300s || true
    kubectl wait --for=condition=ready pod -l app=rabbitmq --timeout=300s || true
    
    print_success "Infrastructure deployed"
}

# Deploy application services
deploy_services() {
    print_info "Deploying application services..."
    
    kubectl apply -f api-gateway/
    kubectl apply -f text-extractor/
    kubectl apply -f media-extractor/
    kubectl apply -f cron-notifier/
    
    print_success "Application services deployed"
}

# Deploy monitoring
deploy_monitoring() {
    print_info "Deploying monitoring (Prometheus, Grafana)..."
    
    kubectl apply -f monitoring/
    
    print_success "Monitoring deployed"
}

# Show status
show_status() {
    print_info "Deployment Status:"
    echo ""
    kubectl get all
    echo ""
    kubectl get pvc
    echo ""
    kubectl get hpa
}

# Show access info
show_access_info() {
    echo ""
    print_info "Access Information:"
    echo ""
    
    # API Gateway
    API_GATEWAY_IP=$(kubectl get service api-gateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    echo "API Gateway: http://$API_GATEWAY_IP"
    echo "  (Set Telegram webhook to: http://$API_GATEWAY_IP/webhook)"
    echo ""
    
    # Grafana
    GRAFANA_IP=$(kubectl get service grafana -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    echo "Grafana: http://$GRAFANA_IP"
    echo "  Login: admin/admin"
    echo ""
    
    # Port-forward commands
    echo "Or use port-forward:"
    echo "  kubectl port-forward service/api-gateway 8000:80"
    echo "  kubectl port-forward service/grafana 3000:80"
    echo "  kubectl port-forward service/prometheus 9090:9090"
}

# Main deployment
main() {
    echo "========================================="
    echo "  Sieve Kubernetes Deployment"
    echo "========================================="
    echo ""
    
    check_prerequisites
    create_namespace
    create_secrets
    apply_configmaps
    deploy_infrastructure
    deploy_services
    deploy_monitoring
    
    echo ""
    print_success "Deployment completed!"
    echo ""
    
    show_status
    show_access_info
    
    echo ""
    print_info "Next steps:"
    echo "  1. Wait for LoadBalancer IPs to be assigned"
    echo "  2. Set Telegram webhook to API Gateway URL"
    echo "  3. Access Grafana to view dashboards"
    echo "  4. Monitor logs: kubectl logs -f deployment/text-extractor"
}

# Run main
main
