#!/usr/bin/env python3

import logging
import yaml

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)
from pprint import pprint


class PostgresCharm(CharmBase):
    state = StoredState()

    def __init__(self, framework, key):
        super().__init__(framework, key)

        self.state.set_default(isStarted=False)

        self.framework.observe(self.on.start, self.on_start)
        self.framework.observe(self.on.stop, self.on_stop)
        self.framework.observe(self.on.update_status, self.on_update_status)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.upgrade_charm, self.on_upgrade_charm)
        self.framework.observe(self.on.leader_elected, self.on_leader_elected)

    def on_start(self, event):
        logging.info('START')
        self.model.unit.status = MaintenanceStatus('Configuring pod')
        podSpec = self.makePodSpec()
        if self.model.unit.is_leader():
            self.model.pod.set_spec(podSpec)
        self.state.isStarted = True
        self.state.podSpec = podSpec
        self.model.unit.status = ActiveStatus('ready')

    def on_stop(self, event):
        logging.info('STOP')
        self.state.isStarted = False

    def on_update_status(self, event):
        logging.info('UPDATE STATUS')

    def on_config_changed(self, event):
        logging.info('CONFIG CHANGED')
        podSpec = self.makePodSpec()
        if hasattr(self.state, 'podSpec') and self.state.podSpec != podSpec:
            self.model.unit.status = MaintenanceStatus('Configuring pod')
            self.model.pod.set_spec(podSpec)
        self.model.unit.status = ActiveStatus('ready')

    def on_upgrade_charm(self, event):
        logging.info('UPGRADING')
        logging.info('UPGRADED')

    def on_leader_elected(self, event):
        logging.info('LEADER ELECTED')

    def makePodSpec(self):
        logging.info('MAKING POD SPEC')
        # with open("src/templates/statefulSet.yml") as spec_file:
        #     podSpecTemplate = spec_file.read()
        podSpec = {
            'securityContext': {'fsGroup': 1001},
            'containers': [{
                'name': 'postgresql',
                # 'image': 'docker.io/bitnami/postgresql:11.7.0-debian-10-r64',
                'image': self.model.config['postgresql-image'],
                'imagePullPolicy': 'IfNotPresent',
                'ports': [{'containerPort': 5432,
                           'name': 'postgresql',
                           'protocol': 'TCP'}],
                'securityContext': {'runAsUser': 1001},
                'livenessProbe': {'exec': {'command': ['sh',
                                                       '-c',
                                                       'PGPASSWORD=$POSTGRES_PASSWORD psql -w -U "postgres" -d "postgres"  -h 127.0.0.1 -c "SELECT 1"']},
                                  'failureThreshold': 6,
                                  'initialDelaySeconds': 30,
                                  'periodSeconds': 10,
                                  'successThreshold': 1,
                                  'timeoutSeconds': 5},
                'readinessProbe': {'exec': {'command': ['sh',
                                                        '-c',
                                                        'PGPASSWORD=$POSTGRES_PASSWORD psql -w -U "postgres" -d "postgres"  -h 127.0.0.1 -c "SELECT 1"']},
                                   'failureThreshold': 6,
                                   'initialDelaySeconds': 5,
                                   'periodSeconds': 10,
                                   'successThreshold': 1,
                                   'timeoutSeconds': 5},
                'config': {
                    'DEBUG': self.model.config['postgresql-debug'],
                    'POSTGRESQL_VOLUME_DIR': "/bitnami/postgresql",
                    'PGDATA': "/bitnami/postgresql/data",
                    'POSTGRES_USER': self.model.config['postgresql-username'],
                    'POSTGRES_PASSWORD': self.model.config['postgresql-password'],
                    'POSTGRES_DB': self.model.config['postgresql-database'],
                    'MY_POD_NAME': "postgresql-0",
                    'REPMGR_NODE_NETWORK_NAME': "$(MY_POD_NAME).postgresql-endpoints.postgresql.svc.cluster.local",
                    # 'MY_POD_NAME': "postgresql-standby-0",
                    # 'REPMGR_NODE_NETWORK_NAME': "$(MY_POD_NAME).postgresql-standby-endpoints.postgresql.svc.cluster.local",
                    'REPMGR_NODE_NAME': "$(MY_POD_NAME)",
                    'REPMGR_UPGRADE_EXTENSION': "no",
                    'REPMGR_PGHBA_TRUST_ALL': "no",
                    'REPMGR_MOUNTED_CONF_DIR': "/bitnami/repmgr/conf",
                    'REPMGR_PARTNER_NODES': "postgresql-0.postgresql-endpoints.postgresql.svc.cluster.local,postgresql-standby-0.postgresql-standby-endpoints.postgresql.svc.cluster.local",
                    'REPMGR_PRIMARY_HOST': "postgresql-0.postgresql-endpoints.postgresql.svc.cluster.local",
                    'REPMGR_LOG_LEVEL': "NOTICE",
                    'REPMGR_CONNECT_TIMEOUT': "5",
                    'REPMGR_RECONNECT_ATTEMPTS': "3",
                    'REPMGR_RECONNECT_INTERVAL': "5",
                    'REPMGR_USERNAME': self.model.config['postgresql-repmgr-username'],
                    'REPMGR_PASSWORD': self.model.config['postgresql-repmgr-password'],
                    'REPMGR_DATABASE': self.model.config['postgresql-repmgr-database'],
                },
            },
            {
                'name': 'metrics',
                'image': self.model.config['metrics-image'],
                'imagePullPolicy': "IfNotPresent",
                'ports': [{'containerPort': 9187,
                           'name': 'metrics',
                           'protocol': 'TCP'}],
                'securityContext': {'runAsUser': 1001},
                'livenessProbe': {'httpGet': {
                                    'path': '/',
                                    'port': 'metrics'},
                                  'failureThreshold': 6,
                                  'initialDelaySeconds': 30,
                                  'periodSeconds': 10,
                                  'successThreshold': 1,
                                  'timeoutSeconds': 5},
                'readinessProbe': {'httpGet': {
                                    'path': '/',
                                    'port': 'metrics'},
                                  'failureThreshold': 6,
                                  'initialDelaySeconds': 30,
                                  'periodSeconds': 10,
                                  'successThreshold': 1,
                                  'timeoutSeconds': 5},
                'config': {
                    'DATA_SOURCE_URI': "127.0.0.1:5432/postgres?sslmode=disable",
                    'DATA_SOURCE_PASS': "postgres",
                    'DATA_SOURCE_USER': "postgres",
                }
            }]
        }
        # data = {}
        # podSpec = podSpecTemplate % data
        # pprint(podSpec)
        # podSpec = yaml.load(podSpec)
        pprint(podSpec)
        return podSpec


if __name__ == "__main__":
    main(PostgresCharm)
