from twisted.internet import reactor

from yakbot.bot import YakbotFactory


if __name__ == '__main__':
    factory = YakbotFactory()

    # TODO: move to config file
    reactor.connectTCP('irc.gamesurge.net', 6667, factory)
    reactor.run()
