#!/usr/bin/python
import shlex
import sys
from collections import defaultdict
from importlib import import_module

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

from yakbot.ext import Plugin, command
from yakbot.utils import comma_andify


class CommandHandlerIRCObject(object):
    """Provides useful convenience methods for command handlers"""

    # TODO: move to config file
    REPLY_WITH_NAME = True

    def __init__(self, yakbot, channel, nick):
        self.yakbot = yakbot
        self.channel = channel
        self.nick = nick

    def _build_text_reply(self, msg):
        if self.REPLY_WITH_NAME:
            msg = '%s: %s' % (self.nick, msg)
        return msg

    def reply(self, msg):
        reply = self._build_text_reply(msg)
        self.yakbot.irc.msg(self.channel, reply)

    def error(self, msg):
        # TODO
        self.reply(msg)


class _MetaCommandsPlugin(Plugin):
    private = True

    @command()
    def help(self, irc, msg, args):
        """Print documentation for a command."""
        command = ' '.join(args).lower()
        if command in self.yakbot.commands:
            handler = self.yakbot.commands[command]
            if handler.__doc__:
                doc = handler.__doc__
            else:
                doc = 'No help found for \x02%s\x02' % command
            irc.reply(doc)
        else:
            irc.error('Command \x02%s\x02 not found' % command)

    @command()
    def list(self, irc, msg, args):
        if args:
            plugin_name = args[0]
            plugin_key = plugin_name.lower()
            if plugin_key not in self.yakbot.plugins:
                irc.error('Plug-in \x02%s\x02 not found.' % plugin_name)
                return

            plugin_commands = self.yakbot.plugin_commands[plugin_key]
            cmd_names = [name for name,_ in plugin_commands]
            cmd_readable = comma_andify(cmd_names)
            num_cmds = len(cmd_names)

            reply = 'Listing %d command%s: %s' % (num_cmds,
                                                  '' if num_cmds == 1 else 's',
                                                  cmd_readable)
            irc.reply(reply)
        else:
            plugin_names = [plugin.name
                            for plugin in self.yakbot.plugins.itervalues()
                            if not plugin.private]
            names_readable = comma_andify(plugin_names)
            length = len(plugin_names)

            reply = 'Listing %d plug-in%s: %s' % (length,
                                                  '' if length == 1 else 's',
                                                  names_readable)
            irc.reply(reply)


class Yakbot(object):
    COMMAND_PREFIX = '!'

    def __init__(self, irc):
        self.irc = irc
        self.plugins = {}
        self.plugin_commands = defaultdict(list)
        self.commands = {}

        self._register_meta_commands()
        self._load_plugins()

    def _parse_command(self, message):
        if not message.startswith('!'):
            return None, None

        command, _, arg_string = message[1:].partition(' ')
        command = command.lower()
        args = self._parse_arguments(arg_string)
        return command, args

    def _parse_arguments(self, arg_string):
        return shlex.split(arg_string)

    def privmsg(self, nick, channel, message):
        command, args = self._parse_command(message)
        if command:
            self.eval_command(nick, channel, message, command, args)

    def eval_command(self, nick, channel, msg, command, args):
        if command not in self.commands:
            return

        irc_obj = CommandHandlerIRCObject(self, channel, nick)
        self.commands[command](irc_obj, msg, args)

    def register_command(self, plugin, command, handler):
        """
        Register a command handler. It should accept three arguments: irc, msg,
        and args. irc is an object used to reply to the command, msg is the
        complete message string, and args is a list of arguments passed to the
        command.
        """
        self.plugin_commands[plugin.name.lower()].append((command, handler))
        self.commands[command] = handler

    def _load_plugins(self):
        # TODO: move to config file
        for name in ('smapi', 'steamid'):
            self.load_plugin('yakbot.plugins.%s' % name)

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
            self._init_plugin(plugin)

            return True, ''

    def _init_plugin(self, plugin):
        self.plugins[plugin.name.lower()] = plugin
        self._load_plugin_commands(plugin)

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
        self._meta_plugin = _MetaCommandsPlugin(self, self.irc)
        self._init_plugin(self._meta_plugin)


class YakbotProtocol(irc.IRCClient):
    """ Son of yakbot """

    # TODO: hardcode this even harder
    nickname = 'yakbot'

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.yakbot = Yakbot(self)

    def signedOn(self):
        # TODO: move to config file
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
