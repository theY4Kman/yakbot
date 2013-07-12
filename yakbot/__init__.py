from argparse import ArgumentParser

from twisted.internet import reactor

from yakbot.bot import YakbotFactory
from yakbot.conf import Settings


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-c', '--conf', help='Path to configuration file',
                        default='yakbot.yaml')

    args = parser.parse_args()
    settings = Settings(args.conf)

    factory = YakbotFactory(settings)

    reactor.connectTCP(settings['network']['host'], settings['network']['port'],
                       factory)
    reactor.run()
