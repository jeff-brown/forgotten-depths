# Deployment Guide - Forgotten Depths MUD

Complete guide for deploying Forgotten Depths MUD to Linode Kubernetes Engine (LKE) using GitHub Actions CI/CD.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [GitHub Actions Setup](#github-actions-setup)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
- `kubectl` (v1.28+)
- Linode CLI (optional but helpful)
- Docker (for local testing)

### Required Accounts
- GitHub account with repository access
- Linode account with LKE cluster

## Initial Setup

### 1. Create Linode Kubernetes Cluster

```bash
# Using Linode CLI
linode-cli lke cluster-create \
  --label forgotten-depths-cluster \
  --region us-east \
  --k8s_version 1.28 \
  --node_pools.type g6-standard-2 \
  --node_pools.count 2

# Or use Linode Cloud Manager:
# https://cloud.linode.com/kubernetes/clusters
```

### 2. Download Kubeconfig

```bash
# Using Linode CLI
linode-cli lke kubeconfig-view <cluster-id> --text | base64 > kubeconfig.b64

# Or download from Cloud Manager and encode:
cat kubeconfig.yaml | base64 > kubeconfig.b64
```

### 3. Test Cluster Access

```bash
# Decode and use kubeconfig
cat kubeconfig.b64 | base64 -d > ~/.kube/config

# Test connection
kubectl cluster-info
kubectl get nodes
```

## GitHub Actions Setup

### 1. Configure GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions**

Add the following secrets:

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `KUBECONFIG` | Base64-encoded kubeconfig file | `cat ~/.kube/config \| base64` |

### 2. Enable GitHub Container Registry

The workflows automatically push images to `ghcr.io/jeff-brown/forgotten-depths`.

Ensure repository has package write permissions:
- **Settings → Actions → General → Workflow permissions**
- Select "Read and write permissions"

### 3. Workflow Files

Two workflows are configured:

#### CI Workflow (`.github/workflows/ci.yaml`)
Triggers on: Pull requests and pushes to `develop`
- Runs tests
- Checks code quality (flake8, black, isort)
- Builds Docker image
- **Does NOT deploy**

#### CD Workflow (`.github/workflows/deploy.yaml`)
Triggers on: Pushes to `main` branch or version tags
- Builds and pushes Docker image to ghcr.io
- Deploys to Kubernetes cluster
- Shows service endpoints

## Kubernetes Deployment

### Architecture

```
┌─────────────────────────────────────────────┐
│         Linode Load Balancers               │
├──────────────────┬──────────────────────────┤
│   Port 4000      │      Port 80             │
│   (Telnet)       │      (Web Client)        │
└────────┬─────────┴──────────┬───────────────┘
         │                    │
    ┌────▼────────────────────▼─────┐
    │    Kubernetes Services        │
    │  - forgotten-depths-telnet    │
    │  - forgotten-depths-web       │
    └────────────┬──────────────────┘
                 │
         ┌───────▼────────┐
         │   Deployment   │
         │  (1 replica)   │
         └───────┬────────┘
                 │
    ┌────────────▼──────────────┐
    │     Pod (MUD Server)      │
    │  - Telnet: 4000           │
    │  - Web: 8080              │
    │                           │
    │  Volumes:                 │
    │  - PV: SQLite database    │
    │  - ConfigMap: configs     │
    │  - EmptyDir: logs         │
    └───────────────────────────┘
```

### Manual Deployment

If you need to deploy manually:

```bash
# 1. Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/persistent-volume.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 2. Check deployment status
kubectl get all -n forgotten-depths

# 3. Wait for LoadBalancers
kubectl get svc -n forgotten-depths -w
```

### Access the Game

Once deployed, get the external IPs:

```bash
# Get Telnet server IP
kubectl get svc forgotten-depths-telnet -n forgotten-depths \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Get Web client IP
kubectl get svc forgotten-depths-web -n forgotten-depths \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Connect using:
- **Telnet**: `telnet <TELNET_IP> 4000`
- **Web**: `http://<WEB_IP>`

## Configuration

### Update Game Settings

Edit `k8s/configmap.yaml` and apply changes:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/forgotten-depths -n forgotten-depths
```

### Scale Resources

Edit `k8s/deployment.yaml` resource limits:

```yaml
resources:
  requests:
    memory: "512Mi"   # Increase if needed
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

Apply changes:
```bash
kubectl apply -f k8s/deployment.yaml
```

**Note**: Replica count must remain `1` for SQLite-based deployment.

## Monitoring and Maintenance

### View Logs

```bash
# Stream logs
kubectl logs -f deployment/forgotten-depths -n forgotten-depths

# Last 100 lines
kubectl logs deployment/forgotten-depths -n forgotten-depths --tail=100

# Follow logs with timestamps
kubectl logs -f deployment/forgotten-depths -n forgotten-depths --timestamps
```

### Check Resource Usage

```bash
# Pod resource usage
kubectl top pods -n forgotten-depths

# Node resource usage
kubectl top nodes
```

### Backup Database

```bash
# Get pod name
POD=$(kubectl get pod -n forgotten-depths -l app=forgotten-depths -o jsonpath='{.items[0].metadata.name}')

# Copy database
kubectl cp forgotten-depths/$POD:/app/data/mud.db ./backup-$(date +%Y%m%d).db
```

### Restore Database

```bash
# Copy database to pod
POD=$(kubectl get pod -n forgotten-depths -l app=forgotten-depths -o jsonpath='{.items[0].metadata.name}')
kubectl cp ./backup.db forgotten-depths/$POD:/app/data/mud.db

# Restart pod to reload
kubectl rollout restart deployment/forgotten-depths -n forgotten-depths
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -n forgotten-depths

# Describe pod for events
kubectl describe pod <pod-name> -n forgotten-depths

# Check logs
kubectl logs <pod-name> -n forgotten-depths
```

### LoadBalancer Pending

Linode LoadBalancers can take 2-5 minutes to provision:

```bash
# Watch service status
kubectl get svc -n forgotten-depths -w

# Check events
kubectl get events -n forgotten-depths --sort-by='.lastTimestamp'
```

### Database Issues

```bash
# Check PVC status
kubectl get pvc -n forgotten-depths

# Describe PVC
kubectl describe pvc forgotten-depths-data -n forgotten-depths

# Check if database file exists
POD=$(kubectl get pod -n forgotten-depths -l app=forgotten-depths -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -n forgotten-depths -- ls -lh /app/data/
```

### Connection Timeouts

Check security group / firewall rules:
- Port 4000 (Telnet) must be open
- Port 80 (Web) must be open

```bash
# Test from outside cluster
telnet <EXTERNAL_IP> 4000

# Test from inside cluster
kubectl run -it --rm debug --image=busybox --restart=Never -- telnet forgotten-depths-telnet.forgotten-depths.svc.cluster.local 4000
```

### Rollback Deployment

```bash
# View rollout history
kubectl rollout history deployment/forgotten-depths -n forgotten-depths

# Rollback to previous version
kubectl rollout undo deployment/forgotten-depths -n forgotten-depths

# Rollback to specific revision
kubectl rollout undo deployment/forgotten-depths -n forgotten-depths --to-revision=2
```

## CI/CD Pipeline Workflow

### Development Workflow

```
1. Create feature branch
   ├─→ Make changes
   ├─→ Push to GitHub
   └─→ Open Pull Request

2. CI runs on PR
   ├─→ Run tests
   ├─→ Check code quality
   ├─→ Build Docker image
   └─→ Report status

3. Merge to main
   ├─→ CD workflow triggers
   ├─→ Build & push image
   ├─→ Deploy to Kubernetes
   └─→ Health check passes
```

### Release Workflow

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0

# CD workflow builds with version tag
# Image tagged as:
# - ghcr.io/jeff-brown/forgotten-depths:v1.0.0
# - ghcr.io/jeff-brown/forgotten-depths:1.0
# - ghcr.io/jeff-brown/forgotten-depths:latest
```

## Cost Optimization

### Linode Costs
- **2x g6-standard-2 nodes**: ~$24/month each = $48/month
- **2x Load Balancers**: ~$10/month each = $20/month
- **Block Storage (10GB)**: ~$1/month
- **Bandwidth**: Included (1TB/month per node)

**Total**: ~$69/month

### Reduce Costs
1. Use 1 node instead of 2 (no high availability)
2. Use smaller node type (g6-standard-1)
3. Combine services into one LoadBalancer with ingress controller

## Security Best Practices

1. **Keep secrets secure**: Never commit KUBECONFIG to git
2. **Use RBAC**: Create service accounts with minimal permissions
3. **Network policies**: Restrict pod-to-pod communication
4. **Update regularly**: Keep Kubernetes and images updated
5. **Monitor logs**: Check for suspicious activity

## Next Steps

1. ✅ Deploy initial cluster
2. ✅ Configure GitHub Actions
3. ✅ First deployment
4. 🔲 Set up monitoring (Prometheus/Grafana)
5. 🔲 Configure automated backups
6. 🔲 Set up alerts (Discord/Slack webhooks)
7. 🔲 Add ingress controller for HTTPS
8. 🔲 Migrate to PostgreSQL for scalability

## Support

- **Issues**: https://github.com/jeff-brown/forgotten-depths/issues
- **Linode Support**: https://www.linode.com/support/
- **Kubernetes Docs**: https://kubernetes.io/docs/

---

Generated with Claude Code
