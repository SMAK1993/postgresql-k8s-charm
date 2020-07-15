from ops.framework import Object, StoredState


class PostgresRepmgr(Object):
    state = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self._relation_name = relation_name
        self._relation = self.framework.model.get_relation(self._relation_name)
        self.framework.observe(charm.on[relation_name].relation_joined, self.on_joined)

    @property
    def _relations(self):
        return self.framework.model.relations[self._relation_name]

    @property
    def is_joined(self):
        return self._relation is not None

    def on_joined(self, event):
        if not self.is_joined:
            event.defer()
            return
        return
