from twisted.internet import reactor

from yakbot.bot import YakbotFactory


if __name__ == '__main__':
    import sys
    factory = YakbotFactory()

    # TODO: move to config file
    host = sys.argv[1] if len(sys.argv) >= 2 else 'irc.gamesurge.net'
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else 6667

    reactor.connectTCP(host, port, factory)
    reactor.run()
