# k8s_operator

This repository contains Kubernetes operators for automating secret synchronization and namespace labeling.

## Operators

### 1. Secret Sync Operator (`secretSync/`)
The **Secret Sync Operator** automates the synchronization of secrets across namespaces based on custom resources.

#### Features:
- Watches for changes in source secrets and updates destination secrets automatically.
- Ensures destination secrets remain in sync, even if modified or deleted manually.
- Prevents infinite sync loops by intelligently handling updates.

For details, see the [`secretSync/README.md`](secretSync/README.md).

### 2. Namespace Auto-Label Operator (`namespaceAutoLabel/`)
The **Namespace Auto-Label Operator** applies predefined labels to Kubernetes namespaces based on `NamespaceLabeller` custom resources.

#### Features:
- Automatically labels namespaces based on `NamespaceLabeller` CR specifications.
- Reacts to namespace updates and applies labels dynamically.
- Updates CR status with the latest applied labels.

For details, see the [`namespaceAutoLabel/README.md`](namespaceAutoLabel/README.md).

## Setup & Deployment
Each operator has its own installation guide and RBAC configurations in their respective directories.
