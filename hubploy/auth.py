"""
Setup authentication from various providers
"""
import json
import os
import subprocess
import shutil

from hubploy.config import get_config


def registry_auth(deployment):
    """
    Do appropriate registry authentication for given deployment
    """
    config = get_config(deployment)

    if 'images' in config and 'registry' in config['images']:
        registry = config['images']['registry']
        provider = registry.get('provider')
        if provider == 'gcloud':
            registry_auth_gcloud(
                deployment, **registry['gcloud']
            )
        elif provider == 'aws':
            registry_auth_aws(
                deployment, **registry['aws']
            )
        else:
            raise ValueError(
                f'Unknown provider {provider} found in hubploy.yaml')


def registry_auth_gcloud(deployment, project, service_key):
    """
    Setup GCR authentication with a service_key

    This changes *global machine state* on where docker can push to!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    subprocess.check_call([
        'gcloud', 'auth',
        'activate-service-account',
        '--key-file', os.path.abspath(service_key_path)
    ])

    subprocess.check_call([
        'gcloud', 'auth', 'configure-docker'
    ])


def registry_auth_aws(deployment, project, zone, service_key):
    """
    Setup AWS authentication to ECR container registry

    This changes *global machine state* on where docker can push to!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )

    if not os.path.isfile(service_key_path):
        raise FileNotFoundError(
            f'The service_key file {service_key_path} does not exist')

    # move credentials to standard location
    cred_dir = os.path.expanduser('~/.aws')
    if not os.path.isdir(cred_dir):
        os.mkdir(cred_dir)
    shutil.copyfile(service_key_path, os.path.join(cred_dir, 'credentials'))

    registry = f'{project}.dkr.ecr.{zone}.amazonaws.com'
    # amazon-ecr-credential-helper installed in .circleci/config.yaml
    # this adds necessary line to authenticate docker with ecr
    dockerConfig = os.path.join(os.path.expanduser('~'), '.docker', 'config.json')
    with open(dockerConfig, 'r') as f:
        config = json.load(f)
        config['credHelpers'][registry] = 'ecr-login'
    with open(dockerConfig, 'w') as f:
        json.dump(config, f)


def cluster_auth(deployment):
    """
    Do appropriate cluster authentication for given deployment
    """
    config = get_config(deployment)

    if 'cluster' in config:
        cluster = config['cluster']
        provider = cluster.get('provider')
        if provider == 'gcloud':
            cluster_auth_gcloud(
                deployment, **cluster['gcloud']
            )
        elif provider == 'aws':
            cluster_auth_aws(
                deployment, **cluster['aws']
            )
        else:
            raise ValueError(
                f'Unknown provider {provider} found in hubploy.yaml')


def cluster_auth_gcloud(deployment, project, cluster, zone, service_key):
    """
    Setup GKE authentication with service_key

    This changes *global machine state* on what current kubernetes cluster is!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    subprocess.check_call([
        'gcloud', 'auth',
        'activate-service-account',
        '--key-file', os.path.abspath(service_key_path)
    ])

    subprocess.check_call([
        'gcloud', 'container', 'clusters',
        f'--zone={zone}',
        f'--project={project}',
        'get-credentials', cluster
    ])


def cluster_auth_aws(deployment, project, cluster, zone, service_key):
    """
    Setup AWS authentication with service_key

    This changes *global machine state* on what current kubernetes cluster is!
    """

    subprocess.check_call(['aws', 'eks', 'update-kubeconfig',
                           '--name', cluster, '--region', zone])
