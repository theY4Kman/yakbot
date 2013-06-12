CMDNAME_ATTR = '__cmdname__'


def command(name=None):
    """ Decorator to register a command handler in a Plugin. """
    def _command(fn):
        setattr(fn, CMDNAME_ATTR, fn.__name__ if name is None else name)
        return fn
    return _command


class PluginMeta(type):
    def __new__(cls, name, bases, attrs):
        plugin = type.__new__(cls, name, bases, attrs)
        if plugin.name is None:
            plugin.name = name

        commands = []
        for name, value in attrs.iteritems():
            if callable(value) and hasattr(value, CMDNAME_ATTR):
                cmdname = getattr(value, CMDNAME_ATTR)
                commands.append((cmdname, value))
        plugin._commands = commands

        return plugin


class Plugin(object):
    __metaclass__ = PluginMeta

    name = None
    _commands = None

    def __init__(self, yakbot):
        self.yakbot = yakbot

    def __hash__(self):
        return hash(self.name)
