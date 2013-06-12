from yakbot.ext import Plugin, command


class Echo(Plugin):
    @command()
    def echo(self, irc, channel, nick, args):
        irc.msg(channel, '%s: %s' % (nick, ' '.join(args)))


plugin_class = Echo
