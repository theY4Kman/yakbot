import re
from urllib2 import urlopen

from yakbot.ext import Plugin, command


RGX_SEARCH_RESULTS = re.compile(r'<a onclick="ShowFunction\((\d+)\)"[^>]*>([^<]+)')
RGX_NOTES = re.compile(r'<b>Notes\s*</b>: <div style="padding-left: 25px;">(.+?)</div>', re.DOTALL)
RGX_PROTOTYPE = re.compile(r'(\([^)]*\))\s*;?\s*(?:</span>|\r|<br />)')
RGX_WHITESPACE = re.compile(r'\s+')


class SMAPI(Plugin):
    @command()
    def smapi(self, channel, nick, msg, args):
        """Lookup a name in the SM API docs."""
        exact = False
        arg_string = ' '.join(args).strip()
        if arg_string[0] == '"' and arg_string[-1] == '"':
            arg_string = arg_string[1:-1]
            exact = True

        lookup = self.DO_LOOKUP(arg_string, exact)
        self.irc.msg(channel, '%s: %s' % (nick, lookup))

    def DO_LOOKUP(self, args, exact=False):
        url = "http://docs.sourcemod.net/api/index.php?action=gethint&id=" + args.replace(" ", "%20")
        page = urlopen(url)
        if not page:
            return "error opening " + url

        contents = page.read()

        matches = RGX_SEARCH_RESULTS.findall(contents)
        length = len(matches)

        if exact is True:
            lowered = args.lower()
            for match in matches:
                if match[1].lower() == lowered:
                    matches[0] = match
                    length = 1

        if length == 0:
            # No results found
            if contents.endswith("0 results found."):
                return "No results found for \x02%s\x02" % (args)

            # Too many results (over 100)
            elif contents.endswith("smaller"):
                return "More than 100 results found for \x02%s\x02. Try a larger query." % (args)

            # Something bad happened if we get here.
            else:
                return "error finding \x02%s\x02" % (args)
        elif length == 1:
            func = matches[0][1]
            func_id = matches[0][0]

            url = "http://docs.sourcemod.net/api/index.php?action=show&id=" + func_id
            page = urlopen(url)

            if not page:
                return "error opening " + url

            contents = page.read()
            notes_match = RGX_NOTES.search(contents)
            proto_match = RGX_PROTOTYPE.search(contents)

            fastload_url = "http://docs.sourcemod.net/api/index.php?fastload=show&id=" + func_id

            if notes_match is None:
                notes = "<no notes>"
            else:
                notes = notes_match.group(1).strip()
                notes = notes.replace("\n", " ").replace("<br />", " ")
                notes = notes.replace('\\"', '"').replace("  ", " ")

            if proto_match is None:
                prototype = "()"
            else:
                prototype = proto_match.group(1).replace("&nbsp;", " ")
                prototype = prototype.replace("<br />", "").replace("&amp;", "&")
                prototype = RGX_WHITESPACE.sub(" ", prototype)

            return "\x02%s\x02%s: %s (%s)" % (func, prototype, notes, fastload_url)
        else:
            answer = ""

            # Append up to six results.
            results_limit = ((length <= 6) and length) or 6

            func_list = ""
            for i in range(results_limit):
                func_list += matches[i][1] + ", "

            if length > 6:
                answer = "First \x026\x02 results of \x02%d\x02: %s\x02...\x02" % (length, func_list)
            else:
                # func_list has a trailing ", " that has to be removed
                answer = "\x02%s\x02 results: %s" % (length, func_list[:-2])

            return answer + " ( http://docs.sourcemod.net/api/index.php?query=%s )" % (args)


plugin_class = SMAPI
