#!/usr/bin/python
import sys

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol


class Yakbot(object):
    COMMAND_PREFIX = '!'

    def __init__(self, irc):
        self.irc = irc

    def _parse_command(self, message):
        if not message.startswith('!'):
            return None, None

        command, arg_string = message[1:].split(' ', 1)
        args = arg_string.split()
        return command, args

    def privmsg(self, nick, channel, message):
        command, args = self._parse_command(message)
        if command:
            self.eval_command(nick, channel, command, args)

    def eval_command(self, nick, channel, command, args):
        pass


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


if __name__ == '__main__':
    factory = YakbotFactory()

    reactor.connectTCP('irc.freenode.net', 6667, factory)
    reactor.run()
