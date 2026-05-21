# Kubernetes Deployment for Sieve

This directory contains Kubernetes manifests for deploying Sieve to a Kubernetes cluster.

## Prerequisites

1. **Kubernetes Cluster** (one of):
   - AWS EKS
   - Google GKE
   - Azure AKS
   - Minikube (local testing)
   - Kind (local testing)

2. **kubectl** installed and configured
   ```bash
   kubectl version --client
   ```

3. **Docker images** pushed to a registry:
   ```bash
   # Build images
   docker build -t your-registry/api-gateway:latest -f api_gateway/Dockerfile .
   docker build -t your-registry/text-extractor:latest -f workers/text_extractor/Dockerfile .
   docker build -t your-registry/media-extractor:latest -f workers/media_extractor/Dockerfile .
   docker build -t your-registry/cron-notifier:latest -f workers/cron_notifier/Dockerfile .
   
   # Push to registry
   docker push your-registry/api-gateway:latest
   docker push your-registry/text-extractor:latest
   docker push your-registry/media-extractor:latest
   docker push your-registry/cron-notifier:latest
   ```

## Quick Start

### 1. Create Namespace
```bash
kubectl apply -f namespace.yaml
kubectl config set-context --current --namespace=sieve
```

### 2. Create Secrets
```bash
kubectl create secret generic sieve-secrets \
  --from-literal=telegram-bot-token=YOUR_TELEGRAM_BOT_TOKEN \
  --from-literal=groq-api-key=YOUR_GROQ_API_KEY \
  --from-literal=google-api-key=YOUR_GOOGLE_API_KEY \
  --namespace=sieve
```

### 3. Apply ConfigMaps
```bash
kubectl apply -f configmap.yaml
kubectl apply -f postgres/configmap.yaml
kubectl apply -f monitoring/prometheus-configmap.yaml
kubectl apply -f monitoring/grafana-configmap.yaml
```

### 4. Deploy Infrastructure (PostgreSQL, Redis, RabbitMQ)
```bash
kubectl apply -f postgres/
kubectl apply -f redis/
kubectl apply -f rabbitmq/
```

Wait for infrastructure to be ready:
```bash
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=ready pod -l app=rabbitmq --timeout=300s
```

### 5. Deploy Application Services
```bash
kubectl apply -f api-gateway/
kubectl apply -f text-extractor/
kubectl apply -f media-extractor/
kubectl apply -f cron-notifier/
```

### 6. Deploy Monitoring
```bash
kubectl apply -f monitoring/
```

### 7. Verify Deployment
```bash
kubectl get all
kubectl get pvc
kubectl get hpa
```

## Directory Structure

```
k8s/
├── namespace.yaml                    # Namespace definition
├── configmap.yaml                    # Application config
├── secrets.yaml.example              # Secrets template (DO NOT commit actual secrets!)
├── postgres/
│   ├── statefulset.yaml             # PostgreSQL StatefulSet
│   ├── service.yaml                 # PostgreSQL Service
│   └── configmap.yaml               # Database init script
├── redis/
│   ├── statefulset.yaml             # Redis StatefulSet
│   └── service.yaml                 # Redis Service
├── rabbitmq/
│   ├── statefulset.yaml             # RabbitMQ StatefulSet
│   └── service.yaml                 # RabbitMQ Service
├── api-gateway/
│   ├── deployment.yaml              # API Gateway Deployment
│   ├── service.yaml                 # API Gateway Service (LoadBalancer)
│   └── ingress.yaml                 # Ingress for HTTPS
├── text-extractor/
│   ├── deployment.yaml              # Text Extractor Deployment
│   ├── service.yaml                 # Text Extractor Service
│   └── hpa.yaml                     # Horizontal Pod Autoscaler
├── media-extractor/
│   ├── deployment.yaml              # Media Extractor Deployment
│   └── service.yaml                 # Media Extractor Service
├── cron-notifier/
│   └── cronjob.yaml                 # CronJob for reminders
├── monitoring/
│   ├── prometheus-deployment.yaml   # Prometheus Deployment
│   ├── prometheus-service.yaml      # Prometheus Service
│   ├── prometheus-configmap.yaml    # Prometheus Config
│   ├── prometheus-pvc.yaml          # Prometheus Storage
│   ├── grafana-deployment.yaml      # Grafana Deployment
│   ├── grafana-service.yaml         # Grafana Service (LoadBalancer)
│   ├── grafana-configmap.yaml       # Grafana Provisioning
│   └── grafana-pvc.yaml             # Grafana Storage
└── README.md                         # This file
```

## Configuration

### Update Image Registry

Before deploying, update the image references in deployment files:

```yaml
# In api-gateway/deployment.yaml, text-extractor/deployment.yaml, etc.
image: your-registry/api-gateway:latest
```

Replace `your-registry` with:
- Docker Hub: `username/image:tag`
- AWS ECR: `123456789.dkr.ecr.region.amazonaws.com/image:tag`
- GCR: `gcr.io/project-id/image:tag`
- Azure ACR: `registry.azurecr.io/image:tag`

### Update Domain

In `api-gateway/ingress.yaml`, replace:
```yaml
host: api.sieve.example.com
```

With your actual domain.

## Accessing Services

### API Gateway (External)
```bash
# Get LoadBalancer IP
kubectl get service api-gateway

# Or use port-forward for testing
kubectl port-forward service/api-gateway 8000:80
```

### Grafana (External)
```bash
# Get LoadBalancer IP
kubectl get service grafana

# Or use port-forward
kubectl port-forward service/grafana 3000:80
# Open http://localhost:3000
# Login: admin/admin
```

### Prometheus (Internal)
```bash
kubectl port-forward service/prometheus 9090:9090
# Open http://localhost:9090
```

### PostgreSQL (Internal)
```bash
kubectl port-forward statefulset/postgres 5432:5432
# Connect: psql -h localhost -U user -d sieve
```

### Redis (Internal)
```bash
kubectl port-forward statefulset/redis 6379:6379
# Connect: redis-cli -h localhost
```

### RabbitMQ Management (Internal)
```bash
kubectl port-forward service/rabbitmq 15672:15672
# Open http://localhost:15672
# Login: guest/guest
```

## Scaling

### Manual Scaling
```bash
# Scale text-extractor to 5 replicas
kubectl scale deployment text-extractor --replicas=5

# Scale api-gateway to 3 replicas
kubectl scale deployment api-gateway --replicas=3
```

### Auto-Scaling (HPA)
Text extractor has HPA configured (2-10 replicas based on CPU/memory):
```bash
# View HPA status
kubectl get hpa

# Describe HPA
kubectl describe hpa text-extractor-hpa

# Edit HPA
kubectl edit hpa text-extractor-hpa
```

## Updating Application

### Rolling Update
```bash
# Update image
kubectl set image deployment/text-extractor \
  text-extractor=your-registry/text-extractor:v2

# Watch rollout
kubectl rollout status deployment/text-extractor

# Check rollout history
kubectl rollout history deployment/text-extractor
```

### Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/text-extractor

# Rollback to specific revision
kubectl rollout undo deployment/text-extractor --to-revision=2
```

## Monitoring

### View Logs
```bash
# All pods
kubectl logs -l app=text-extractor

# Specific pod
kubectl logs text-extractor-xxx

# Follow logs
kubectl logs -f text-extractor-xxx

# Previous crashed container
kubectl logs text-extractor-xxx --previous
```

### View Metrics
```bash
# Node metrics
kubectl top nodes

# Pod metrics
kubectl top pods

# Specific pod
kubectl top pod text-extractor-xxx
```

### View Events
```bash
kubectl get events --sort-by=.metadata.creationTimestamp
```

## Troubleshooting

### Pod Not Starting
```bash
# Describe pod
kubectl describe pod <pod-name>

# Check events
kubectl get events

# Check logs
kubectl logs <pod-name>
```

### Service Not Accessible
```bash
# Check service
kubectl get service <service-name>

# Check endpoints
kubectl get endpoints <service-name>

# Test connectivity from another pod
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
wget -O- http://api-gateway:8000
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
kubectl get pod -l app=postgres

# Check PostgreSQL logs
kubectl logs postgres-0

# Test connection
kubectl exec -it postgres-0 -- psql -U user -d sieve -c "SELECT 1;"
```

### Out of Resources
```bash
# Check resource usage
kubectl top nodes
kubectl top pods

# Check resource requests/limits
kubectl describe pod <pod-name>
```

## Backup & Restore

### PostgreSQL Backup
```bash
# Create backup
kubectl exec postgres-0 -- pg_dump -U user sieve > backup-$(date +%Y%m%d).sql

# Restore backup
cat backup-20260511.sql | kubectl exec -i postgres-0 -- psql -U user sieve
```

### Volume Snapshots
```bash
# Create snapshot (if supported by storage class)
kubectl apply -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot
  namespace: sieve
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: postgres-data-postgres-0
EOF
```

## Cleanup

### Delete All Resources
```bash
# Delete all resources in namespace
kubectl delete all --all -n sieve

# Delete PVCs
kubectl delete pvc --all -n sieve

# Delete namespace
kubectl delete namespace sieve
```

### Delete Specific Resources
```bash
kubectl delete -f api-gateway/
kubectl delete -f text-extractor/
kubectl delete -f postgres/
```

## Production Checklist

- [ ] Use managed databases (RDS, Cloud SQL) instead of StatefulSets
- [ ] Use managed Redis (ElastiCache, Memorystore)
- [ ] Use managed RabbitMQ (AWS MQ, CloudAMQP)
- [ ] Set up proper secrets management (AWS Secrets Manager, Vault)
- [ ] Configure Ingress with TLS/SSL certificates
- [ ] Set up monitoring alerts (Prometheus Alertmanager)
- [ ] Configure log aggregation (ELK, Loki)
- [ ] Set up backup automation
- [ ] Configure network policies
- [ ] Set up pod disruption budgets
- [ ] Configure resource quotas
- [ ] Set up CI/CD pipeline
- [ ] Configure multi-region deployment
- [ ] Set up disaster recovery plan

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- See `docs/KUBERNETES.md` for detailed guide

---

Last Updated: 2026-05-11
