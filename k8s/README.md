# Kubernetes Manifests

Kubernetes configuration files for deploying Forgotten Depths MUD to Linode Kubernetes Engine (LKE).

## Quick Start

```bash
# Deploy everything
kubectl apply -f k8s/

# Or deploy in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/persistent-volume.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Files

| File | Description |
|------|-------------|
| `namespace.yaml` | Creates `forgotten-depths` namespace |
| `configmap.yaml` | Game configuration (server, database, game settings) |
| `persistent-volume.yaml` | 10GB volume for SQLite database |
| `deployment.yaml` | Main application deployment (1 replica) |
| `service.yaml` | LoadBalancers for Telnet (4000) and Web (80) |

## Access

Get service IPs:
```bash
# Telnet server
kubectl get svc forgotten-depths-telnet -n forgotten-depths

# Web client
kubectl get svc forgotten-depths-web -n forgotten-depths
```

Connect:
- **Telnet**: `telnet <IP> 4000`
- **Web**: `http://<IP>`

## Common Commands

```bash
# View logs
kubectl logs -f deployment/forgotten-depths -n forgotten-depths

# Restart deployment
kubectl rollout restart deployment/forgotten-depths -n forgotten-depths

# Check status
kubectl get all -n forgotten-depths

# Backup database
POD=$(kubectl get pod -n forgotten-depths -l app=forgotten-depths -o jsonpath='{.items[0].metadata.name}')
kubectl cp forgotten-depths/$POD:/app/data/mud.db ./backup.db

# Shell into pod
kubectl exec -it deployment/forgotten-depths -n forgotten-depths -- /bin/bash
```

## Notes

- **Single replica only**: SQLite doesn't support horizontal scaling
- **Storage class**: Uses `linode-block-storage-retain` for data persistence
- **LoadBalancers**: Linode provisions public IPs automatically
- **Session affinity**: Enabled for persistent player connections

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for complete documentation.
