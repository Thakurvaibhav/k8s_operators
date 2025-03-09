# Namespace Label Operator

The **Namespace Label Operator** automatically applies labels to Kubernetes namespaces based on custom resources (CRs). It ensures that specified labels are consistently applied and updated when necessary.

## How It Works

The operator watches for **NamespaceLabeller** custom resources (CRs) and applies the defined labels to the target namespace. It also updates labels when the CR is modified.

## Example Custom Resource (CR)

```yaml
apiVersion: ops.dev/v1
kind: NamespaceLabeller
metadata:
  name: ns1-labels
spec:
  targetNamespace: ns1
  targetLabels:
    app: demo-app
    environment: dev
    service: demo-service
```

### Explanation:
- **`targetNamespace: ns1`** → The namespace where labels should be applied.
- **`targetLabels`** → Key-value pairs of labels that will be added to the namespace.

## Installation

### Deploy the Operator
To deploy the operator, apply the required manifests:

```sh
kubectl apply -f manifests/deploy
```

## Usage

1. **Create a NamespaceLabeller CR**  
   Apply a CR to label a namespace:

   ```sh
   kubectl apply -f namespace-labeller-cr.yaml
   ```

2. **Verify Labels**  
   Check if the labels were applied:

   ```sh
   kubectl get namespace ns1 --show-labels
   ```

3. **Update Labels**  
   Modify the `targetLabels` in the CR and reapply it:

   ```sh
   kubectl apply -f namespace-labeller-cr.yaml
   ```

4. **Monitor Operator Logs**  
   View logs to debug or confirm label application:

   ```sh
   kubectl logs -l app=namespace-label-operator -n kube-system
   ```

## Cleanup

To remove the operator and its CRDs:

```sh
kubectl delete -f manifests/deploy
```

## Contributions

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License.
```
