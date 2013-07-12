import os
from UserDict import IterableUserDict

import yaml


def recursive_dict_update(d, u):
    """http://stackoverflow.com/a/3233356/148585"""
    for k, v in u.iteritems():
        if isinstance(v, dict):
            r = recursive_dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class Settings(IterableUserDict):
    def __init__(self, path):
        self.path = path
        self.data = {}

        self._load_defaults()
        self._load_file(self.path)

    def _load_file(self, path):
        if not os.path.exists(path):
            return False
        with open(path) as fp:
            recursive_dict_update(self.data, yaml.safe_load(fp))
        return True

    def _load_defaults(self):
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
