# Kubernetes Guide for Sieve

## Why Kubernetes?

### The Problem Kubernetes Solves

**Docker Compose Limitations:**
- ❌ Single host only (can't span multiple servers)
- ❌ No automatic scaling
- ❌ No self-healing (manual restart needed)
- ❌ No rolling updates (downtime during deployment)
- ❌ No load balancing across multiple instances
- ❌ No resource management
- ❌ No high availability

**Kubernetes Solutions:**
- ✅ Multi-host orchestration
- ✅ Automatic horizontal scaling (HPA)
- ✅ Self-healing (auto-restart failed pods)
- ✅ Zero-downtime deployments
- ✅ Built-in load balancing
- ✅ Resource quotas & limits
- ✅ High availability & fault tolerance

---

## Why Kubernetes for Sieve?

### 1. **Automatic Scaling**

**Scenario:** Exam season → 10x more messages

**Docker Compose:**
```bash
# Manual scaling
docker-compose up -d --scale text_extractor=10
# Have to monitor and scale manually
```

**Kubernetes:**
```yaml
# Automatic scaling based on CPU
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70
```
**Result:** Automatically scales from 2 to 20 instances based on load

---

### 2. **High Availability**

**Docker Compose:**
- Single server fails → Entire system down
- No redundancy

**Kubernetes:**
- Multi-node cluster (3+ nodes)
- Pods distributed across nodes
- Node fails → Pods automatically rescheduled to healthy nodes
- **Zero downtime**

---

### 3. **Zero-Downtime Deployments**

**Docker Compose:**
```bash
docker-compose down          # ❌ Downtime starts
docker-compose up --build    # ❌ Still down
# Users can't use bot during deployment
```

**Kubernetes:**
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0      # Always keep at least 1 pod running
    maxSurge: 1            # Create 1 new pod before killing old
```
**Result:** New version deployed with zero downtime

---

### 4. **Self-Healing**

**Docker Compose:**
- Container crashes → Manual restart needed
- Service unhealthy → No automatic recovery

**Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
```
**Result:** Unhealthy pods automatically restarted

---

### 5. **Resource Management**

**Docker Compose:**
- No resource limits
- One service can consume all CPU/memory
- Hard to predict costs

**Kubernetes:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```
**Result:** Guaranteed resources + cost predictability

---

### 6. **Multi-Region Deployment**

**Scenario:** Users in India + US

**Docker Compose:**
- Single region only
- High latency for distant users

**Kubernetes:**
- Deploy to multiple regions (Mumbai + Virginia)
- Route users to nearest region
- **Lower latency**

---

## Kubernetes Architecture for Sieve

### Cluster Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    Control Plane                        │ │
│  │  (API Server, Scheduler, Controller Manager, etcd)     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Node 1     │  │   Node 2     │  │   Node 3     │     │
│  │              │  │              │  │              │     │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │     │
│  │ │api-gateway│ │  │ │api-gateway│ │  │ │text-extr │ │     │
│  │ │  Pod 1   │ │  │ │  Pod 2   │ │  │ │  Pod 1   │ │     │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │     │
│  │              │  │              │  │              │     │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │     │
│  │ │text-extr │ │  │ │text-extr │ │  │ │cron-notif│ │     │
│  │ │  Pod 2   │ │  │ │  Pod 3   │ │  │ │  Pod 1   │ │     │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Persistent Storage (PVCs)                  │ │
│  │  PostgreSQL Data │ Redis Data │ Prometheus Data        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Resource Mapping

| Docker Compose | Kubernetes | Purpose |
|----------------|------------|---------|
| `api_gateway` | Deployment + Service (LoadBalancer) | External access |
| `text_extractor` | Deployment + HPA | Auto-scaling worker |
| `media_extractor` | Deployment | Image processing |
| `cron_notifier` | CronJob | Scheduled reminders |
| `postgres` | StatefulSet + PVC | Stateful database |
| `redis` | StatefulSet + PVC | Stateful cache |
| `rabbitmq` | StatefulSet + PVC | Message queue |
| `prometheus` | Deployment + PVC | Metrics |
| `grafana` | Deployment + PVC | Dashboards |

---

## Kubernetes Manifests

I'll create all the necessary Kubernetes YAML files in `k8s/` directory.

### Directory Structure
```
k8s/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml
├── postgres/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── redis/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── rabbitmq/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── api-gateway/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── text-extractor/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── media-extractor/
│   ├── deployment.yaml
│   └── service.yaml
├── cron-notifier/
│   └── cronjob.yaml
├── monitoring/
│   ├── prometheus-deployment.yaml
│   ├── prometheus-service.yaml
│   ├── grafana-deployment.yaml
│   └── grafana-service.yaml
└── README.md
```

---

## Kubernetes Commands Reference

### Cluster Management

#### 1. View Cluster Info
```bash
kubectl cluster-info
kubectl get nodes
kubectl top nodes
```

---

#### 2. Create Namespace
```bash
kubectl create namespace sieve
kubectl config set-context --current --namespace=sieve
```

---

### Deployment Commands

#### 3. Apply Manifests
```bash
# Apply all manifests
kubectl apply -f k8s/

# Apply specific file
kubectl apply -f k8s/api-gateway/deployment.yaml

# Apply directory
kubectl apply -f k8s/postgres/
```

---

#### 4. View Resources
```bash
# View all resources
kubectl get all

# View specific resources
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get statefulsets
kubectl get pvc
kubectl get hpa

# Watch resources (live updates)
kubectl get pods -w
```

---

#### 5. View Pod Details
```bash
# Describe pod
kubectl describe pod <pod-name>

# View pod logs
kubectl logs <pod-name>

# Follow logs
kubectl logs -f <pod-name>

# Logs from previous crashed container
kubectl logs <pod-name> --previous

# Logs from specific container in pod
kubectl logs <pod-name> -c <container-name>
```

---

#### 6. Execute Commands in Pod
```bash
# Run command
kubectl exec <pod-name> -- <command>

# Interactive shell
kubectl exec -it <pod-name> -- bash

# Examples
kubectl exec -it postgres-0 -- psql -U user -d sieve
kubectl exec -it redis-0 -- redis-cli
kubectl exec -it text-extractor-xxx -- python
```

---

#### 7. Port Forwarding
```bash
# Forward local port to pod
kubectl port-forward pod/<pod-name> 8000:8000

# Forward to service
kubectl port-forward service/api-gateway 8000:8000

# Forward to StatefulSet
kubectl port-forward statefulset/postgres 5432:5432
```

---

#### 8. Scale Deployments
```bash
# Manual scaling
kubectl scale deployment text-extractor --replicas=5

# View current replicas
kubectl get deployment text-extractor
```

---

#### 9. Update Deployments
```bash
# Update image
kubectl set image deployment/text-extractor \
  text-extractor=your-registry/text-extractor:v2

# Rollout status
kubectl rollout status deployment/text-extractor

# Rollout history
kubectl rollout history deployment/text-extractor

# Rollback to previous version
kubectl rollout undo deployment/text-extractor

# Rollback to specific revision
kubectl rollout undo deployment/text-extractor --to-revision=2
```

---

#### 10. Delete Resources
```bash
# Delete specific resource
kubectl delete pod <pod-name>
kubectl delete deployment <deployment-name>

# Delete from file
kubectl delete -f k8s/api-gateway/deployment.yaml

# Delete all resources in namespace
kubectl delete all --all -n sieve

# Delete namespace (deletes everything inside)
kubectl delete namespace sieve
```

---

### Debugging Commands

#### 11. Check Pod Status
```bash
# Why is pod not running?
kubectl describe pod <pod-name>

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check resource usage
kubectl top pod <pod-name>
```

---

#### 12. Debug Network Issues
```bash
# Test service connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Inside pod:
wget -O- http://api-gateway:8000/health

# Check service endpoints
kubectl get endpoints api-gateway
```

---

#### 13. Check Secrets & ConfigMaps
```bash
# View secrets (base64 encoded)
kubectl get secret sieve-secrets -o yaml

# Decode secret
kubectl get secret sieve-secrets -o jsonpath='{.data.telegram-bot-token}' | base64 -d

# View ConfigMap
kubectl get configmap sieve-config -o yaml
```

---

### Monitoring Commands

#### 14. View Metrics
```bash
# Node metrics
kubectl top nodes

# Pod metrics
kubectl top pods

# Specific pod
kubectl top pod text-extractor-xxx
```

---

#### 15. View HPA Status
```bash
# View autoscaler
kubectl get hpa

# Describe autoscaler
kubectl describe hpa text-extractor-hpa

# Watch autoscaler
kubectl get hpa -w
```

---

## Deployment Workflow

### 1. Initial Setup

```bash
# 1. Create namespace
kubectl create namespace sieve

# 2. Set default namespace
kubectl config set-context --current --namespace=sieve

# 3. Create secrets
kubectl create secret generic sieve-secrets \
  --from-literal=telegram-bot-token=YOUR_TOKEN \
  --from-literal=groq-api-key=YOUR_KEY \
  --from-literal=google-api-key=YOUR_KEY

# 4. Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# 5. Deploy infrastructure (PostgreSQL, Redis, RabbitMQ)
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/
kubectl apply -f k8s/rabbitmq/

# 6. Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=ready pod -l app=rabbitmq --timeout=300s

# 7. Deploy application services
kubectl apply -f k8s/api-gateway/
kubectl apply -f k8s/text-extractor/
kubectl apply -f k8s/media-extractor/
kubectl apply -f k8s/cron-notifier/

# 8. Deploy monitoring
kubectl apply -f k8s/monitoring/

# 9. Check status
kubectl get all
```

---

### 2. Update Application

```bash
# 1. Build new image
docker build -t your-registry/text-extractor:v2 -f workers/text_extractor/Dockerfile .

# 2. Push to registry
docker push your-registry/text-extractor:v2

# 3. Update deployment
kubectl set image deployment/text-extractor \
  text-extractor=your-registry/text-extractor:v2

# 4. Watch rollout
kubectl rollout status deployment/text-extractor

# 5. Verify
kubectl get pods
kubectl logs -f deployment/text-extractor
```

---

### 3. Rollback

```bash
# 1. Check rollout history
kubectl rollout history deployment/text-extractor

# 2. Rollback to previous version
kubectl rollout undo deployment/text-extractor

# 3. Verify
kubectl rollout status deployment/text-extractor
```

---

### 4. Scale Application

```bash
# Manual scaling
kubectl scale deployment text-extractor --replicas=10

# Or edit HPA
kubectl edit hpa text-extractor-hpa
# Change maxReplicas: 20
```

---

## Production Best Practices

### 1. Resource Requests & Limits

**Always set both:**
```yaml
resources:
  requests:      # Guaranteed resources
    memory: "256Mi"
    cpu: "250m"
  limits:        # Maximum allowed
    memory: "512Mi"
    cpu: "500m"
```

**Why?**
- Requests: Kubernetes uses this for scheduling
- Limits: Prevents one pod from consuming all resources

---

### 2. Health Checks

**Liveness Probe:** Is the container alive?
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

**Readiness Probe:** Is the container ready to serve traffic?
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

### 3. Rolling Update Strategy

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0    # Always keep at least 1 pod running
    maxSurge: 1          # Create 1 new pod before killing old
```

---

### 4. Pod Disruption Budget

**Prevent too many pods from being down:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: text-extractor-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: text-extractor
```

---

### 5. Network Policies

**Restrict traffic between pods:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-gateway-policy
spec:
  podSelector:
    matchLabels:
      app: api-gateway
  ingress:
  - from:
    - podSelector: {}  # Allow from all pods in namespace
    ports:
    - protocol: TCP
      port: 8000
```

---

### 6. Secrets Management

**Use external secret managers:**
- AWS Secrets Manager
- HashiCorp Vault
- Google Secret Manager

**Example with AWS:**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: sieve-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
  target:
    name: sieve-secrets
  data:
  - secretKey: telegram-bot-token
    remoteRef:
      key: sieve/telegram-bot-token
```

---

## Cost Optimization

### 1. Right-Size Resources

**Monitor actual usage:**
```bash
kubectl top pods
```

**Adjust requests/limits based on actual usage**

---

### 2. Use Spot Instances (AWS)

**For non-critical workloads:**
```yaml
nodeSelector:
  node.kubernetes.io/instance-type: spot
tolerations:
- key: "spot"
  operator: "Equal"
  value: "true"
  effect: "NoSchedule"
```

---

### 3. Cluster Autoscaler

**Automatically add/remove nodes:**
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: ClusterAutoscaler
spec:
  scaleDown:
    enabled: true
    delayAfterAdd: 10m
```

---

## Monitoring & Observability

### 1. Prometheus Metrics

**Access Prometheus:**
```bash
kubectl port-forward service/prometheus 9090:9090
# Open http://localhost:9090
```

**Key Metrics:**
- `container_cpu_usage_seconds_total`
- `container_memory_usage_bytes`
- `rabbitmq_queue_messages`
- `http_requests_total`

---

### 2. Grafana Dashboards

**Access Grafana:**
```bash
kubectl port-forward service/grafana 3000:3000
# Open http://localhost:3000
```

---

### 3. Logging

**Centralized logging with ELK/Loki:**
```bash
# Install Loki
helm install loki grafana/loki-stack

# View logs in Grafana
# Add Loki as datasource
```

---

## Disaster Recovery

### 1. Backup Strategy

**PostgreSQL:**
```bash
# Create backup
kubectl exec postgres-0 -- pg_dump -U user sieve > backup.sql

# Restore
cat backup.sql | kubectl exec -i postgres-0 -- psql -U user sieve
```

**Persistent Volumes:**
```bash
# Use VolumeSnapshots
kubectl apply -f k8s/postgres/volume-snapshot.yaml
```

---

### 2. Multi-Region Setup

**Deploy to multiple regions:**
- Primary: us-east-1
- Secondary: ap-south-1

**Use Global Load Balancer:**
- Route53 (AWS)
- Cloud Load Balancing (GCP)

---

## Comparison: Docker Compose vs Kubernetes

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐⭐ Complex |
| **Learning Curve** | ⭐ Easy | ⭐⭐⭐⭐⭐ Steep |
| **Scaling** | Manual | Automatic |
| **High Availability** | ❌ No | ✅ Yes |
| **Self-Healing** | ❌ No | ✅ Yes |
| **Rolling Updates** | ❌ No | ✅ Yes |
| **Multi-Host** | ❌ No | ✅ Yes |
| **Cost** | $ Low | $$$ High |
| **Best For** | Dev, Small Apps | Production, Scale |

---

## When to Use Kubernetes?

### ✅ Use Kubernetes When:
- Production deployment
- Need high availability (99.9%+ uptime)
- Need auto-scaling
- Multiple regions
- Large scale (1000+ users)
- Team has Kubernetes expertise

### ❌ Don't Use Kubernetes When:
- Development environment
- Small scale (<100 users)
- Single server sufficient
- Team lacks Kubernetes knowledge
- Budget constrained

---

## Migration Path

### Phase 1: Docker Compose (Current)
- Development
- Testing
- Small deployments

### Phase 2: Kubernetes (Future)
- Production
- Auto-scaling
- High availability

**Recommendation:** Start with Docker Compose, migrate to Kubernetes when needed.

---

## Summary

**Kubernetes Benefits for Sieve:**
1. ✅ Auto-scaling (handle exam season traffic)
2. ✅ High availability (99.9% uptime)
3. ✅ Zero-downtime deployments
4. ✅ Self-healing (auto-restart failures)
5. ✅ Multi-region support
6. ✅ Resource management
7. ✅ Production-ready

**Key Commands:**
```bash
kubectl apply -f k8s/              # Deploy
kubectl get all                    # Status
kubectl logs -f <pod>              # Logs
kubectl exec -it <pod> -- bash     # Shell
kubectl scale deployment <name>    # Scale
kubectl rollout undo deployment    # Rollback
```

**Next Steps:**
1. Review k8s/ manifests
2. Set up Kubernetes cluster (EKS/GKE/AKS)
3. Deploy to staging
4. Test thoroughly
5. Deploy to production

---

Last Updated: 2026-05-11
