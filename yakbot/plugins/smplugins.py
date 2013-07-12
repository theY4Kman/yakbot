import json
from urllib import urlencode
from urllib2 import urlopen

from yakbot.ext import Plugin, command


class SearchPluginsError(Exception):
    pass


def plugin_search(title=None, author=None, approved=None):
    args = {}
    if title:
        args['title'] = title
    if author:
        args['author'] = author

    if approved is not None:
        args['approved'] = int(approved)
    url_args = urlencode(args)

    page = urlopen('http://users.alliedmods.net/~they4kman/plugin_search.php?' + url_args)
    if not page:
        raise SearchPluginsError('Could not reach plug-in search.')

    return json.loads(page.read())


class SMPlugins(Plugin):
    @command(aliases=('pl',))
    def plugins(self, irc, msg, args):
        """<plug-in title>"""
        exact = False
        search = ' '.join(args)

        if str(msg).strip().endswith('"' + search + '"'):
            exact = True

        irc.reply(self._get_plugin_search_reply(search, "title", exact))

    @command(aliases=('pla',))
    def pluginsauthor(self, irc, msg, args):
        """<plug-in author>"""
        exact = False
        search = ' '.join(args)

        if str(msg).strip().endswith('"' + search + '"'):
            exact = True

        irc.reply(self._get_plugin_search_reply(search, "author", exact))

    def _get_plugin_search_reply(self, args, criterion, exact):
        unicode_reply = unicode(self._do_plugin_search(args, criterion, exact))
        return unicode_reply.encode('ascii', 'replace')

    def _do_plugin_search(self, args, criterion, exact):
        search_terms = args
        url = "http://sourcemod.net/plugins.php?search=1&%s=%s" % (criterion, search_terms)

        db_search_terms = search_terms.replace('%', '\\%').replace('*', '%')
        if not exact:
            db_search_terms = '%' + db_search_terms + '%'

        search_args = { criterion: db_search_terms }
        plugins = plugin_search(**search_args)

        length = len(plugins)
        if length == 0:
            # No results found
            return "No results found for \x02%s\x02" % args
        elif length == 1:
            plugin = plugins[0]
            return "\x02%s\x02, by %s: %s  "\
                "( http://forums.alliedmods.net/showthread.php?p=%s )" % (plugin['title'], plugin['author'],
                                                                          plugin['description'], plugin['postid'])
        elif length < 7:
            return "Displaying \x02%d\x02 results: %s ( %s )" % (length, ",".join(map(lambda o: o['title'], plugins)),
                                                                 url)
        else:
            return "First \x026\x02 results of \x02%d\x02: %s ( %s )" % (length, ", ".join(map(lambda o: o['title'],
                                                                                               plugins[:6])), url)


plugin_class = SMPlugins
