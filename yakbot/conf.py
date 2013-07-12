import os
from UserDict import IterableUserDict

import yaml


class Settings(IterableUserDict):
    def __init__(self, path):
        self.path = path
        self.data = {}

        if not self._load_file(self.path):
            self._load_defaults()

    def _load_file(self, path):
        if not os.path.exists(path):
            return False
        with open(path) as fp:
            self.data = yaml.safe_load(fp)
        return True

    def _load_defaults(self):
        # TODO: load this first, and have _load_file recursively update self.data
        # Note "recursive". An update() will no descend into dicts, losing data
        self.data = yaml.safe_load('''
            channels:
            - '#sourcemod'
            - '#yakbot'
            network:
              host: irc.gamesurge.net
              port: 6667
            nickname: yakbot
            plugins:
            - smapi
            - steamid
            - smplugins
            reply-with-name: true
        ''')

    def _save_to_file(self, path):
        with open(path, 'w') as fp:
            fp.write(yaml.safe_dump(self.data, default_flow_style=False))

    def flush(self):
        self._save_to_file(self.path)

    def __setitem__(self, key, value):
        IterableUserDict.__setitem__(self, key, value)
        self.flush()

    def update(self, dict=None, **kwargs):
        IterableUserDict.update(self, dict, **kwargs)
        self.flush()
