from twisted.internet import reactor

from yakbot.bot import YakbotFactory


if __name__ == '__main__':
    factory = YakbotFactory()

    reactor.connectTCP('localhost', 6667, factory)
    reactor.run()
