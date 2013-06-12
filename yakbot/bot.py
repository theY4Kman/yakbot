#!/usr/bin/python
import sys
from collections import defaultdict
from importlib import import_module

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol


class Yakbot(object):
    COMMAND_PREFIX = '!'

    def __init__(self, irc):
        self.irc = irc
        self.plugins = {}
        self.plugin_commands = defaultdict(list)
        self.commands = {}

        self._register_meta_commands()

        self.load_plugin('yakbot.plugins.smapi')

    def _parse_command(self, message):
        if not message.startswith('!'):
            return None, None

        command, _, arg_string = message[1:].partition(' ')
        args = self._parse_arguments(arg_string)
        return command, args

    def _parse_arguments(self, arg_string):
        return arg_string.split(' ')

    def privmsg(self, nick, channel, message):
        command, args = self._parse_command(message)
        if command:
            self.eval_command(nick, channel, message, command, args)

    def eval_command(self, nick, channel, msg, command, args):
        if command not in self.commands:
            return

        self.commands[command](channel, nick, msg, args)

    def register_command(self, plugin, command, handler):
        """
        Register a command handler. It should accept four arguments: channel,
        nick, msg, and args. msg is the complete message string, and args is a
        list of arguments passed to the command.
        """
        self.plugin_commands[plugin].append((command, handler))
        self.commands[command] = handler

    def _load_plugin(self, name):
        try:
            module = import_module(name)
        except ImportError as err:
            return False, 'Import error: %s' % err.message
        else:
            if not hasattr(module, 'plugin_class'):
                return False, 'No `plugin_class` global found'

            plugin_class = module.plugin_class
            plugin = plugin_class(self, self.irc)

            self.plugins[plugin.name] = plugin
            self._load_plugin_commands(plugin)

            return True, ''

    def load_plugin(self, name):
        print 'Attempting to load plug-in', name
        success, message = self._load_plugin(name)
        if success:
            print 'Success!'
        else:
            print 'Error:', message

    def _load_plugin_commands(self, plugin):
        for cmdname, handler in plugin._commands:
            bound_handler = handler.__get__(plugin, plugin.__class__)
            self.register_command(plugin, cmdname, bound_handler)

    def _register_meta_commands(self):
        self.register_command(None, 'help', self._help_command)

    def _help_command(self, channel, nick, msg, args):
        """Print documentation for a command."""
        command = ' '.join(args)
        if command in self.commands:
            handler = self.commands[command]
            if handler.__doc__:
                doc = handler.__doc__
            else:
                doc = 'No help found for \x02%s\x02' % command
            self.irc.msg(channel, '%s: %s' % (nick, doc))
        else:
            self.irc.msg(channel, '%s: Command \x02%s\x02 not found' % (nick, command))


class YakbotProtocol(irc.IRCClient):
    """ Son of yakbot """

    nickname = 'yakbot'

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.yakbot = Yakbot(self)

    def signedOn(self):
        self.join('#yakbot')

    def privmsg(self, user, channel, message):
        nick = user.split('!', 1)[0]
        self.yakbot.privmsg(nick, channel, message)


class YakbotFactory(protocol.ClientFactory):
    def buildProtocol(self, addr):
        yakbot = YakbotProtocol()
        yakbot.factory = self
        return yakbot

    def clientConnectionLost(self, connector, reason):
        print 'Reconnecting...'
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print >> sys.stderr, 'Connection failed:', reason
        reactor.stop()
