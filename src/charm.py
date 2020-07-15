#!/usr/bin/env python3

import logging
import yaml

from ops.charm import CharmBase, CharmEvents
from ops.main import main
from ops.framework import EventBase, EventSource, StoredState
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
    BlockedStatus
)
from repmgr import PostgresRepmgr

from pprint import pprint

class RepmgrEvent(EventBase):
    def __init__(self, handle):
        super().__init__(handle)

    def snapshot(self):
        return

    def restore(self):
        return

class PostgresCharmEvents(CharmEvents):
    cluster_initialized = EventSource(RepmgrEvent)

class PostgresCharm(CharmBase):
    on = PostgresCharmEvents()
    state = StoredState()

    def __init__(self, framework, key):
        super().__init__(framework, key)

        self.state.set_default(isStarted=False)
        self.state.podSpec = ""

        self.primary = PostgresRepmgr(self, 'primary')
        self.standby = PostgresRepmgr(self, 'standby')

        self.framework.observe(self.on.start, self.on_start)
        self.framework.observe(self.on.stop, self.on_stop)
        self.framework.observe(self.on.update_status, self.on_update_status)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.upgrade_charm, self.on_upgrade_charm)
        self.framework.observe(self.on.leader_elected, self.on_leader_elected)
        self.framework.observe(self.on.primary_relation_joined, self.on_primary_relation_joined)
        self.framework.observe(self.on.primary_relation_departed, self.on_primary_relation_departed)
        self.framework.observe(self.on.standby_relation_joined, self.on_standby_relation_joined)
        self.framework.observe(self.on.standby_relation_departed, self.on_standby_relation_departed)

    def on_start(self, event):
        logging.info('START')
        self.model.unit.status = MaintenanceStatus('Configuring pod')
        if not self.primary.is_joined and not self.standby.is_joined:
          self.model.unit.status = BlockedStatus('No primary or standby relation established')
          return
        podSpec = self.makePodSpec()
        if self.model.unit.is_leader():
            pprint('SET POD SPEC')
            self.model.pod.set_spec(podSpec)
        self.state.isStarted = True
        self.state.podSpec = podSpec
        self.model.unit.status = ActiveStatus('ready')

    def on_stop(self, event):
        logging.info('STOP')
        self.state.isStarted = False

    def on_update_status(self, event):
        logging.info('UPDATE STATUS')
        if not self.primary.is_joined and not self.standby.is_joined:
          self.model.unit.status = BlockedStatus('No primary or standby relation established')
          return

    def on_config_changed(self, event):
        logging.info('CONFIG CHANGED')
        if not self.primary.is_joined and not self.standby.is_joined:
          self.model.unit.status = BlockedStatus('No primary or standby relation established')
          return
        podSpec = self.makePodSpec()
        if self.state.podSpec != podSpec:
            self.model.unit.status = MaintenanceStatus('Configuring pod')
            self.state.podSpec = podSpec
            if self.model.unit.is_leader():
                pprint('SET POD SPEC')
                # self.model.pod.set_spec(podSpec)
        self.model.unit.status = ActiveStatus('ready')

    def on_upgrade_charm(self, event):
        logging.info('UPGRADING')
        logging.info('UPGRADED')

    def on_leader_elected(self, event):
        logging.info('LEADER ELECTED')

    def on_primary_relation_joined(self, event):
        logging.info('PRIMARY JOINED')
        if not self.primary.is_joined and not self.standby.is_joined:
          self.model.unit.status = BlockedStatus('No primary or standby relation established')
          return
        podSpec = self.makePodSpec()
        if self.state.podSpec != podSpec:
            self.model.unit.status = MaintenanceStatus('Configuring pod')
            self.state.podSpec = podSpec
            if self.model.unit.is_leader():
                pprint('SET POD SPEC')
                self.model.pod.set_spec(podSpec)
        self.model.unit.status = ActiveStatus('ready')

    def on_primary_relation_departed(self, event):
        logging.info('PRIMARY DEPARTED')
        podSpec = self.makePodSpec()
        if self.state.podSpec != podSpec:
            self.model.unit.status = MaintenanceStatus('Configuring pod')
            self.state.podSpec = podSpec
            if self.model.unit.is_leader():
                pprint('SET POD SPEC')
                self.model.pod.set_spec(podSpec)
        self.model.unit.status = ActiveStatus('ready')

    def on_standby_relation_joined(self, event):
        logging.info('STANDBY JOINED')
        if not self.primary.is_joined and not self.standby.is_joined:
          self.model.unit.status = BlockedStatus('No primary or standby relation established')
          return
        podSpec = self.makePodSpec()
        if self.state.podSpec != podSpec:
            self.model.unit.status = MaintenanceStatus('Configuring pod')
            self.state.podSpec = podSpec
            if self.model.unit.is_leader():
                pprint('SET POD SPEC')
                self.model.pod.set_spec(podSpec)
        self.model.unit.status = ActiveStatus('ready')

    def on_standby_relation_departed(self, event):
        logging.info('STANDBY DEPARTED')
        podSpec = self.makePodSpec()
        if self.state.podSpec != podSpec:
            self.model.unit.status = MaintenanceStatus('Configuring pod')
            self.state.podSpec = podSpec
            if self.model.unit.is_leader():
                pprint('SET POD SPEC')
                self.model.pod.set_spec(podSpec)
        self.model.unit.status = ActiveStatus('ready')

    def makePodSpec(self):
        logging.info('MAKING POD SPEC')
        appName = self.model.unit.app.name
        pprint(appName)
        # podName = (self.model.unit.name).replace('/', '-')
        # pprint(podName)
        partnerNodes = ""
        standbyRelation = self.model.get_relation("standby")
        # pprint(standbyRelation)
        if standbyRelation != None:
            # pprint(standbyRelation)
            partnerNodes += standbyRelation.app.name + "-0." + standbyRelation.app.name + "-endpoints." + self.model.name + ".svc.cluster.local,"
        partnerNodes += appName + "-0." + appName + "-endpoints." + self.model.name + ".svc.cluster.local,"
        primaryRelation = self.model.get_relation("primary")
        # pprint(primaryRelation)
        if primaryRelation != None:
            # pprint(primaryRelation)
            partnerNodes += primaryRelation.app.name + "-0." + primaryRelation.app.name + "-endpoints." + self.model.name + ".svc.cluster.local,"
        partnerNodes = partnerNodes.rstrip(',')
        pprint(partnerNodes)
        repmgrPrimaryNode = standbyRelation.app.name if standbyRelation != None else appName
        podSpec = {
            "version": 3, 
            "containers": [
              {
                "name": "postgresql",
                'image': self.model.config['postgresql-image'], 
                "imagePullPolicy": "IfNotPresent", 
                "ports": [
                  {
                    "protocol": "TCP", 
                    "name": "postgresql", 
                    "containerPort": 5432
                  }
                ], 
                "envConfig": {
                  # "REPMGR_PARTNER_NODES": "postgresql-0.postgresql-endpoints.postgresql.svc.cluster.local,postgresql-standby-0.postgresql-standby-endpoints.postgresql.svc.cluster.local", 
                  "REPMGR_PARTNER_NODES": partnerNodes, 
                  "REPMGR_RECONNECT_INTERVAL": "5", 
                  "REPMGR_PASSWORD": "repmgr", 
                  "POSTGRES_PASSWORD": "postgres", 
                  "MY_POD_NAME": appName + "-0", 
                  "POSTGRES_DB": "postgres", 
                  "PGDATA": "/bitnami/postgresql/data", 
                  "REPMGR_UPGRADE_EXTENSION": "no", 
                  "REPMGR_NODE_NETWORK_NAME": "$(MY_POD_NAME)." + appName + "-endpoints." + self.model.name + ".svc.cluster.local", 
                  "REPMGR_DATABASE": "repmgr", 
                  "REPMGR_NODE_NAME": "$(MY_POD_NAME)", 
                  "REPMGR_RECONNECT_ATTEMPTS": "3", 
                  "POSTGRES_USER": "postgres", 
                  "REPMGR_LOG_LEVEL": "NOTICE", 
                  "BITNAMI_DEBUG": "true", 
                  "REPMGR_CONNECT_TIMEOUT": "5", 
                  "REPMGR_MOUNTED_CONF_DIR": "/bitnami/repmgr/conf", 
                  "REPMGR_PRIMARY_HOST": repmgrPrimaryNode + "-0." + repmgrPrimaryNode + "-endpoints." + self.model.name + ".svc.cluster.local", 
                  # "REPMGR_PRIMARY_HOST": "postgresql-0.postgresql-endpoints.postgresql.svc.cluster.local", 
                  "POSTGRESQL_VOLUME_DIR": "/bitnami/postgresql", 
                  "REPMGR_PGHBA_TRUST_ALL": "no", 
                  "REPMGR_USERNAME": "repmgr"
                }, 
              }, 
              {
                "name": "metrics",
                'image': self.model.config['metrics-image'],
                "imagePullPolicy": "IfNotPresent", 
                "ports": [
                  {
                    "protocol": "TCP", 
                    "name": "metrics", 
                    "containerPort": 9187
                  }
                ], 
                "envConfig": {
                  "DATA_SOURCE_URI": "127.0.0.1:5432/postgres?sslmode=disable", 
                  "DATA_SOURCE_PASS": "postgres", 
                  "DATA_SOURCE_USER": "postgres"
                } 
              }
            ]
          }
        pprint(podSpec)
        return podSpec


if __name__ == "__main__":
    main(PostgresCharm)
