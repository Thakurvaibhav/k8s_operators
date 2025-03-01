import kopf
from kubernetes import client, config, watch
from kubernetes.client import CoreV1Api
from config import Config
import time

# Create an operator which looks for a CR and copies secrets as per its spec. The CR should be something like
# apiVersion: ops.dev/v1
# kind: SecretCopy
# metadata:
#   name: es-exporter-copy
#   namespace: vaibhav-test
# spec:
#   sourceNamespace: monitoring
#   sourceSecret: es-exporter
# Set up logging
logger = Config.setup_logging()
cluster = Config.cluster()

@kopf.on.create('ops.dev', 'v1', 'secretcopies')
@kopf.on.update('ops.dev', 'v1', 'secretcopies')
def create_update_secpy(spec, name, namespace, status, logger, **kwargs):
    logger.info(f"Creat_Update triggered for secpy: {name}")
    sync_secpy(spec, name, namespace, status, logger, **kwargs)

@kopf.on.delete('ops.dev', 'v1', 'secretcopies')
def delete_secpy(spec, name, namespace, logger, **kwargs):
    api = kubeconfig()
    targetSecret = spec.get('targetSecret', name)
    targetNamespace = namespace
    logger.info(f"Detected deletion of secpy: {name}")

    logger.info(f"Deleting secret named {targetSecret} in {targetNamespace}")
    api.delete_namespaced_secret(targetSecret, targetNamespace)

def find_relevant_secretcopies(secret_name, secret_namespace, logger):
    api = client.CustomObjectsApi()
    secretcopies = api.list_cluster_custom_object('ops.dev', 'v1', 'secretcopies')
    relevant = []
    for secpy in secretcopies['items']:
        name = secpy['metadata']['name']
        namespace = secpy['metadata']['namespace']
    
        sourceNamespace = secpy['spec'].get('sourceNamespace')
        sourceSecret = secpy['spec'].get('sourceSecret')

        targetSecret = secpy['spec'].get('targetSecret', name)
        targetNamespace = namespace

        if sourceNamespace == secret_namespace and sourceSecret == secret_name:
            logger.info(f"Found SecretCopy CR for source {secret_name}/{secret_namespace}: {name}")
            relevant.append((secpy, 'source'))
        if targetNamespace == secret_namespace and targetSecret == secret_name:
            logger.info(f"Found SecretCopy CR for target {secret_name}/{secret_namespace}: {name}")
            relevant.append((secpy,'target'))
    return relevant

def initial_sync():
    api = kubeconfig()
    api = client.CustomObjectsApi()
    secretcopies = api.list_cluster_custom_object('ops.dev', 'v1', 'secretcopies')
    logger.info(f"Initial sync for {len(secretcopies['items'])} SecretCopy CRs")

    for secpy in secretcopies['items']:
        logger.info(f"Initial sync for {secpy['metadata']['namespace']}/{secpy['metadata']['name']}")
        trigger_sync(secpy)

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

def sync_secpy(spec, name, namespace, status, logger, **kwargs):
    api = kubeconfig()
    logger.info(f"Sync triggered for secpy: {name}")

    targetSecret = spec.get('targetSecret', name)
    targetNamespace = namespace
    sourceNamespace = spec.get('sourceNamespace')
    sourceSecret = spec.get('sourceSecret')

    try:
        secret = api.read_namespaced_secret(sourceSecret, sourceNamespace)
    except client.exceptions.ApiException as e:
        logger.error(f"Error reading secret: {e}")
        return {'message': f"Error reading secret: {e}", 'condition': False}
    secretData = secret.data
    secretStringData = secret.string_data
    secretLabels = secret.metadata.labels
    secretType = secret.type

    logger.info(f"Creating secret named {targetSecret} in {targetNamespace}")
    target_secret_manifest = client.V1Secret(
        api_version='v1',
        kind='Secret',
        metadata=client.V1ObjectMeta(name=targetSecret, namespace=targetNamespace, labels=secretLabels),
        data=secretData,
        string_data=secretStringData,
        type=secretType)
    
    try:
        api.create_namespaced_secret(targetNamespace, target_secret_manifest)
        return {'message': f"Secret created: {targetSecret}/{targetNamespace}", 'condition': True}
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.warning(f"Error creating secret: {e}. Trying replace")
            api.replace_namespaced_secret(targetSecret, targetNamespace, target_secret_manifest)
            return {'message': f"Secret updated: {targetSecret}/{targetNamespace}", 'condition': True}
        else:
            logger.error(f"Error creating secret: {e}")
            return {'message': f"Error creating secret: {e}", 'condition': False}

def trigger_sync(secretcopy):
    name = secretcopy['metadata']['name']
    namespace = secretcopy['metadata']['namespace']
    spec = secretcopy['spec']
    sync_secpy(spec, name, namespace, None, logger)

@kopf.on.event('', 'v1', 'secrets')
def watch_secret(event, logger, **kwargs):
    secret = event['object']
    secret_name = secret['metadata']['name']
    secret_namespace = secret['metadata']['namespace']

    # Check if this is a secret we care about (linked to any SecretCopy CR)
    secret_copies = find_relevant_secretcopies(secret_name, secret_namespace, logger)
    for secretcopy, relation in secret_copies:
        if relation == 'source':
            if event['type'] in ['MODIFIED', 'ADDED']:
                logger.info(f"Source Secret {secret_namespace}/{secret_name} changed. Triggering sync for {secretcopy['metadata']['name']}.")
                trigger_sync(secretcopy)
        if relation == 'target':
            if event['type'] == 'MODIFIED':      
                logger.warning(f"Target Secret {secret_namespace}/{secret_name} modified. Triggering sync for {secretcopy['metadata']['name']}.")
                trigger_sync(secretcopy)
            elif event['type'] == 'DELETED':
                logger.warning(f"Target Secret {secret_namespace}/{secret_name} deleted. Triggering sync for {secretcopy['metadata']['name']}.")
                trigger_sync(secretcopy)

def main():
    initial_sync()
    kopf.run()

if __name__ == '__main__':
    main()
