# Secret Sync Operator

## Overview
The **Secret Sync Operator** is a Kubernetes operator built using [Kopf](https://github.com/nolar/kopf). It watches for custom resources (CRs) that define secret synchronization rules and ensures that secrets are copied across namespaces as specified.

## Features
- Watches for `SecretSync` custom resources.
- Automatically copies secrets from source namespaces to destination namespaces.
- Keeps the destination secrets updated when the source secret changes.
- Prevents infinite loops by detecting and handling updates properly.

## Installation

### Prerequisites
- Kubernetes cluster (v1.22+ recommended)
- [`kubectl`](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [`kopf`](https://github.com/nolar/kopf) installed
- Python 3.8+

### Deploy the Operator

**Apply the resources:**
   ```sh
   kubectl apply -f manifests/deploy
   ```

## Usage

### Define a SecretSync CR
Create a `SecretSync` resource to specify a secret to sync:
```yaml
apiVersion: ops.dev/v1
kind: SecretCopy
metadata:
  name: ns-1-secret
  namespace: my-ns-2
spec:
  sourceNamespace: my-ns-1
  sourceSecret: my-source-secret
  targetSecret: ns-1-secret
```
Apply it with:
```sh
kubectl apply -f secret-sync.yaml
```

### Verify Sync
Check if the secret has been copied:
```sh
kubectl get secrets -n my-ns-2 ns-1-secret
```

## Development

### Running Locally
To test locally using a kubeconfig:
```sh
pip install -r requirements.txt
python secret-sync.py
```

### Logs
Check the logs of the operator:
```sh
kubectl logs -l k8s-app=secret-sync-operator
```

## Cleanup
To remove the operator and all related resources:
```sh
kubectl delete -f manifests/deploy
```

## License
MIT License

