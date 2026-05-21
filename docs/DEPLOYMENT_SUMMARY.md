# Deployment Summary - Docker & Kubernetes

## Overview

Sieve can be deployed in two ways:
1. **Docker Compose** - For development and small deployments
2. **Kubernetes** - For production and scale

---

## Docker Compose Deployment

### When to Use
- ✅ Development environment
- ✅ Single server deployment
- ✅ Quick testing
- ✅ Small scale (<100 users)
- ✅ Budget constrained

### Pros
- Simple setup (one command)
- Easy to understand
- Low resource requirements
- Fast iteration

### Cons
- Single host only
- No auto-scaling
- Manual failover
- Limited monitoring

### Quick Start
```bash
# 1. Clone repo
git clone <repo-url>
cd sieve

# 2. Create .env file
cp .env.example .env
# Edit .env with your tokens

# 3. Start services
docker-compose up -d

# 4. Check logs
docker-compose logs -f

# 5. Access services
# API Gateway: http://localhost:8000
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

### Documentation
See `docs/DOCKER.md` for complete guide

---

## Kubernetes Deployment

### When to Use
- ✅ Production deployment
- ✅ High availability required (99.9%+ uptime)
- ✅ Auto-scaling needed
- ✅ Multiple regions
- ✅ Large scale (1000+ users)

### Pros
- Auto-scaling (HPA)
- Self-healing
- Zero-downtime deployments
- Multi-region support
- Advanced monitoring
- High availability

### Cons
- Complex setup
- Steep learning curve
- Higher costs
- Requires Kubernetes expertise

### Quick Start
```bash
# 1. Prerequisites
# - Kubernetes cluster (EKS/GKE/AKS)
# - kubectl configured
# - Docker images pushed to registry

# 2. Deploy
cd k8s
chmod +x deploy.sh
./deploy.sh

# 3. Check status
kubectl get all -n sieve

# 4. Access services
# Get LoadBalancer IPs
kubectl get service -n sieve
```

### Documentation
See `docs/KUBERNETES.md` for complete guide

---

## Architecture Comparison

### Docker Compose Architecture
```
┌─────────────────────────────────────┐
│         Single Host                  │
│                                      │
│  ┌──────────┐  ┌──────────┐        │
│  │api-gateway│  │text-extr │        │
│  └──────────┘  └──────────┘        │
│                                      │
│  ┌──────────┐  ┌──────────┐        │
│  │PostgreSQL│  │  Redis   │        │
│  └──────────┘  └──────────┘        │
└─────────────────────────────────────┘
```

### Kubernetes Architecture
```
┌─────────────────────────────────────────────────┐
│            Kubernetes Cluster                    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Node 1  │  │  Node 2  │  │  Node 3  │     │
│  │          │  │          │  │          │     │
│  │ api-gw-1 │  │ api-gw-2 │  │text-ext-1│     │
│  │text-ext-2│  │text-ext-3│  │ postgres │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                  │
│  Load Balancer + Auto-scaling + Self-healing    │
└─────────────────────────────────────────────────┘
```

---

## Feature Comparison

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| **Setup Time** | 5 minutes | 1-2 hours |
| **Learning Curve** | Easy | Steep |
| **Scaling** | Manual | Automatic |
| **High Availability** | ❌ No | ✅ Yes |
| **Self-Healing** | ❌ No | ✅ Yes |
| **Rolling Updates** | ❌ No | ✅ Yes |
| **Multi-Host** | ❌ No | ✅ Yes |
| **Resource Limits** | Basic | Advanced |
| **Monitoring** | Basic | Advanced |
| **Cost** | $ Low | $$$ High |
| **Maintenance** | Low | High |

---

## Migration Path

### Phase 1: Development (Docker Compose)
**Duration:** Ongoing

**Setup:**
```bash
docker-compose up -d
```

**Use for:**
- Local development
- Testing
- Prototyping

---

### Phase 2: Staging (Kubernetes)
**Duration:** 1-2 weeks

**Setup:**
```bash
# Deploy to staging cluster
cd k8s
./deploy.sh
```

**Test:**
- Load testing
- Failover scenarios
- Scaling behavior
- Monitoring setup

---

### Phase 3: Production (Kubernetes)
**Duration:** Ongoing

**Setup:**
```bash
# Deploy to production cluster
cd k8s
./deploy.sh
```

**Monitor:**
- Grafana dashboards
- Prometheus alerts
- Application logs
- Resource usage

---

## Resource Requirements

### Docker Compose (Single Host)

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB
- Network: 100 Mbps

**Recommended:**
- CPU: 8 cores
- RAM: 16 GB
- Disk: 100 GB
- Network: 1 Gbps

**Estimated Cost:** $50-100/month (single VPS)

---

### Kubernetes (Cluster)

**Minimum (3 nodes):**
- Node 1: 2 CPU, 4 GB RAM (control plane + workers)
- Node 2: 2 CPU, 4 GB RAM (workers)
- Node 3: 2 CPU, 4 GB RAM (workers)
- Total: 6 CPU, 12 GB RAM

**Recommended (3 nodes):**
- Node 1: 4 CPU, 8 GB RAM
- Node 2: 4 CPU, 8 GB RAM
- Node 3: 4 CPU, 8 GB RAM
- Total: 12 CPU, 24 GB RAM

**Estimated Cost:** $200-500/month (managed Kubernetes)

---

## Scaling Comparison

### Docker Compose Scaling

**Manual scaling:**
```bash
docker-compose up -d --scale text_extractor=5
```

**Limitations:**
- Single host only
- Manual intervention required
- No automatic scale-down
- No resource-based scaling

---

### Kubernetes Scaling

**Automatic scaling (HPA):**
```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilization: 70%
```

**Benefits:**
- Automatic scale-up/down
- Resource-based (CPU, memory)
- Custom metrics support
- Multi-node distribution

**Example:**
- Normal load: 2 replicas
- Exam season: Auto-scales to 10 replicas
- After peak: Auto-scales down to 2 replicas

---

## Monitoring Comparison

### Docker Compose Monitoring

**Tools:**
- Prometheus (metrics)
- Grafana (dashboards)
- Docker logs

**Access:**
```bash
# Grafana
http://localhost:3000

# Prometheus
http://localhost:9090

# Logs
docker-compose logs -f
```

---

### Kubernetes Monitoring

**Tools:**
- Prometheus (metrics)
- Grafana (dashboards)
- Kubernetes Dashboard
- kubectl logs

**Access:**
```bash
# Grafana
kubectl port-forward service/grafana 3000:80

# Prometheus
kubectl port-forward service/prometheus 9090:9090

# Logs
kubectl logs -f deployment/text-extractor

# Metrics
kubectl top pods
```

**Additional Features:**
- Pod-level metrics
- Node-level metrics
- Resource quotas
- Custom metrics
- Alerting

---

## Deployment Checklist

### Docker Compose Checklist

- [ ] Install Docker & Docker Compose
- [ ] Clone repository
- [ ] Create .env file with tokens
- [ ] Run `docker-compose up -d`
- [ ] Verify services: `docker-compose ps`
- [ ] Check logs: `docker-compose logs -f`
- [ ] Access Grafana: http://localhost:3000
- [ ] Set Telegram webhook
- [ ] Test bot functionality

---

### Kubernetes Checklist

**Pre-deployment:**
- [ ] Set up Kubernetes cluster (EKS/GKE/AKS)
- [ ] Install kubectl
- [ ] Configure kubectl context
- [ ] Build Docker images
- [ ] Push images to registry
- [ ] Update image references in manifests
- [ ] Update domain in ingress.yaml

**Deployment:**
- [ ] Run `./k8s/deploy.sh`
- [ ] Verify namespace: `kubectl get ns`
- [ ] Verify pods: `kubectl get pods -n sieve`
- [ ] Verify services: `kubectl get svc -n sieve`
- [ ] Verify PVCs: `kubectl get pvc -n sieve`
- [ ] Verify HPA: `kubectl get hpa -n sieve`

**Post-deployment:**
- [ ] Get LoadBalancer IPs
- [ ] Configure DNS records
- [ ] Set up TLS certificates
- [ ] Set Telegram webhook
- [ ] Configure monitoring alerts
- [ ] Test bot functionality
- [ ] Load testing
- [ ] Backup strategy

---

## Cost Estimation

### Docker Compose (Monthly)

| Item | Cost |
|------|------|
| VPS (8 CPU, 16 GB RAM) | $80 |
| Storage (100 GB) | $10 |
| Bandwidth (1 TB) | $10 |
| **Total** | **~$100** |

---

### Kubernetes (Monthly)

| Item | Cost |
|------|------|
| Managed Kubernetes (EKS/GKE) | $70 |
| 3 Worker Nodes (4 CPU, 8 GB each) | $300 |
| Load Balancer | $20 |
| Storage (100 GB) | $10 |
| Bandwidth (1 TB) | $10 |
| **Total** | **~$410** |

**Note:** Costs vary by cloud provider and region

---

## Recommendations

### For Development
**Use Docker Compose**
- Fast iteration
- Easy debugging
- Low cost
- Simple setup

### For Small Production (<100 users)
**Use Docker Compose**
- Sufficient for small scale
- Lower costs
- Easier maintenance
- Can migrate to Kubernetes later

### For Large Production (>1000 users)
**Use Kubernetes**
- Auto-scaling required
- High availability needed
- Multi-region support
- Advanced monitoring

### For Growing Startups
**Start with Docker Compose, migrate to Kubernetes**
1. Launch with Docker Compose
2. Validate product-market fit
3. Grow user base
4. Migrate to Kubernetes when needed

---

## Support & Documentation

### Docker Compose
- **Guide:** `docs/DOCKER.md`
- **Commands:** `docs/DOCKER.md#docker-commands-reference`
- **Troubleshooting:** `docs/DOCKER.md#troubleshooting`

### Kubernetes
- **Guide:** `docs/KUBERNETES.md`
- **Commands:** `docs/KUBERNETES.md#kubernetes-commands-reference`
- **Manifests:** `k8s/`
- **Deploy Script:** `k8s/deploy.sh`
- **Cleanup Script:** `k8s/cleanup.sh`

---

## Quick Reference

### Docker Compose Commands
```bash
docker-compose up -d              # Start
docker-compose down               # Stop
docker-compose logs -f            # Logs
docker-compose ps                 # Status
docker-compose restart            # Restart
docker-compose up -d --build      # Rebuild
```

### Kubernetes Commands
```bash
kubectl get all -n sieve          # Status
kubectl logs -f <pod>             # Logs
kubectl describe pod <pod>        # Details
kubectl exec -it <pod> -- bash    # Shell
kubectl scale deployment <name>   # Scale
kubectl rollout undo deployment   # Rollback
```

---

Last Updated: 2026-05-11
