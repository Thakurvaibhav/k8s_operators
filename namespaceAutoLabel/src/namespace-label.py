import kopf
from kubernetes import client, config
from config import Config
from datetime import datetime, timezone

# Create an operator which looks for a CR and copies secrets as per its spec. The CR should be something like
""" apiVersion: ops.dev/v1
kind: NamespaceLabeller
metadata:
  name: vt-test-labels
spec:
  targetNamespace: vt-test
  targetLabels:
    app: vt-test
    team: engineering
    environment: dev """
logger = Config.setup_logging()
cluster = Config.cluster()

@kopf.on.startup()
def initial_sync(logger, **kwargs):
    api = kubeconfig()
    api = client.CustomObjectsApi()
    namespacelabellers = api.list_cluster_custom_object('ops.dev', 'v1', 'namespacelabellers')
    logger.info(f"Initial sync for {len(namespacelabellers['items'])} NamespaceLabeller CRs")

    for namespacelabeller in namespacelabellers['items']:
        logger.info(f"Initial sync for {namespacelabeller['metadata']['name']}")
        label_namespace(namespacelabeller['spec'],namespacelabeller['metadata']['name'], logger)

def kubeconfig() -> client.CoreV1Api:
    """This is for using the kubeconfig to auth with the k8s api
    with the first try it will try to use the in-cluster config (so for in cluster use)
    If it cannot find an incluster because it is running locally, it will use your local config"""
    try:
        # Try to load the in-cluster configuration
        config.load_incluster_config()
        logger.info("Loaded in-cluster configuration.")
    except config.ConfigException:
        # If that fails, fall back to kubeconfig file
        config.load_kube_config(context=cluster)
        logger.info(f"Loaded kubeconfig file with context {cluster}.")

        # Check the active context
        _, active_context = config.list_kube_config_contexts()
        if active_context:
            logger.info(f"The active context is {active_context['name']}.")
        else:
            logger.info("No active context.")

    # Now you can use the client
    api = client.CoreV1Api()
    return api

def label_namespace(spec, name, logger, **kwargs):
    api = kubeconfig()
    targetNamespace = spec.get('targetNamespace')
    logger.info(f"Namespace Labeller is: {name}")
    ns = api.read_namespace(name=targetNamespace)
    targetNamespaceAnnotations = ns.metadata.annotations or {}
    targetNamespaceLabels = ns.metadata.labels or {}


    logger.info(f"Getting namespace annotations: {targetNamespaceAnnotations}")

    if targetNamespaceAnnotations.get('ops.dev/namespacelabeller'):
        if targetNamespaceAnnotations['ops.dev/namespacelabeller']:
            logger.info(f'Labels should be added to {targetNamespace}')
    else:
        logger.info(f'Labels should not be added to {targetNamespace}')
        return {'message': f"Target ns does not have relevant annotation", 'condition': False}
    targetNamespaceLabels.update(spec.get('targetLabels'))
    logger.info(f"Updating namespace labels: {targetNamespaceLabels}")
    try:
        api.patch_namespace(name=targetNamespace, body={'metadata': {'labels': targetNamespaceLabels}})
        logger.info(f"Namespace labels updated successfully for {targetNamespace}")
        return {'message': f"Namespace labels updated successfully for {targetNamespace}", 'condition': True}
    except client.exceptions.ApiException as e:
        logger.error(f"Error updating namespace labels: {e}")
        return {'message': f"Error updating namespace labels: {e}", 'condition': False}

def now():
    return datetime.now(timezone.utc).isoformat()

@kopf.on.create('ops.dev', 'v1', 'namespacelabellers')
@kopf.on.update('ops.dev', 'v1', 'namespacelabellers')
def create_update_namespaces(spec, name, logger, **kwargs):
    logger.info(f"Creat_Update triggered for NamespaceLabeller: {name}")
    result = label_namespace(spec, name, logger, **kwargs)
    return {
        'lastUpdated': now(),
        'labelsApplied': result['condition'],
        'message': result['message']
    }

@kopf.on.update('', 'v1', 'namespaces')
def namespace_update(name, **kwargs):
    api = client.CustomObjectsApi()
    logger.info(f"Namespace update triggered for: {name}")
    annotations = kwargs['meta'].get('annotations', {})
    if 'ops.dev/namespacelabeller' not in annotations:
        logger.info(f"Namespace {name} does not have labeller annotation, skipping.")
        return
    namespacelabellers = find_relevant_namespacelabellers(name, logger)
    for namespacelabeller in namespacelabellers:
        result = label_namespace(namespacelabeller['spec'], namespacelabeller['metadata']['name'], logger)
        status = {
            "create_update_namespaces": {
            "lastUpdated": now(),
            "labelsApplied": result['condition'],
            "message": result['message']
            }
        }
        try:
            api.patch_cluster_custom_object(
                group='ops.dev',
                version='v1',
                plural='namespacelabellers',
                name=namespacelabeller['metadata']['name'],
                body={'status': status}
            )
            logger.info(f"Updated status for NamespaceLabeller CR: {namespacelabeller['metadata']['name']}")
        except client.exceptions.ApiException as e:
            logger.error(f"Error updating status for NamespaceLabeller CR: {namespacelabeller['metadata']['name']}, error: {e}")

def find_relevant_namespacelabellers(name, logger, **kwargs):
    api = client.CustomObjectsApi()
    namespacelabellers = api.list_cluster_custom_object('ops.dev', 'v1', 'namespacelabellers')
    relevant = []
    for namespacelabeller in namespacelabellers['items']:
        targetNamespace = namespacelabeller['spec'].get('targetNamespace')
        if targetNamespace == name:
            logger.info(f"Found NamespaceLabeller CR for targetNamespace: {name}")
            relevant.append(namespacelabeller)
        else:
            logger.warning(f"Not relevant NamespaceLabeller CR for targetNamespace: {name}")
    return relevant

def main():
    kopf.run()

if __name__ == '__main__':
    main()