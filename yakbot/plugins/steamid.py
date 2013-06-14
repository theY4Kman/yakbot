import re
import urllib
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from yakbot.ext import Plugin, command


class SteamIDError(Exception):
  pass


class SteamCommunityProfile:
    """
    Class that, given necessary details, returns all information on a Steam
    Community profile.
    """

    rgx_steamid64 = re.compile(r'<steamID64>(\d+)</steamID64>', re.I)
    rgx_steamid = re.compile(r"STEAM_[0-5]:([01]):([0-9]+)", re.I) # group 1, 2
    rgx_commid = re.compile(r"(https?:\/\/steamcommunity\.com\/(profiles?|id)\/)?([0-9]{17,18})/?", re.I) # group 3
    rgx_userid = re.compile(r"(https?:\/\/steamcommunity\.com\/(profiles?|id)\/)?([^\/]+)/?", re.I) # group 3
    rgx_addfriend = re.compile(r"var ajaxFriendUrl = \"http://steamcommunity.com/actions/AddFriendAjax/([0-9]{17,18})\";")
    rgx_player_search = re.compile(r'''<div class="resultItem">\s*<div class="pgtag">Player</div>\s*<div class="groupBlockMedium">\s*<div class="mediumHolder_default"><div class="avatarMedium"><a href="(?P<url>[^"]+)">''')

    MAX_LEVELS_OF_RECURSION = 10

    @staticmethod
    def STEAMID2COMMID(match):
        iServer = int(match.group(1))
        iFriend = int(match.group(2)) * 2
        iFriend += 76561197960265728 + iServer

        return iFriend

    @staticmethod
    def COMMID2STEAMID(commid):
        iFriend = int(commid)

        iServer = iFriend % 2
        iFriend -= iServer + 76561197960265728
        iFriend /= 2

        return "STEAM_0:%d:%d" % ( iServer, iFriend )

    @staticmethod
    def USERID2COMMID(userid, level=0):
        url = "http://steamcommunity.com/id/%s?xml=1" % userid
        page = urllib.urlopen(url)
        if not page:
            raise SteamIDError("error connecting to profile page.")

        match = SteamCommunityProfile.rgx_steamid64.search(page.read())
        if match is None:
            url = "http://steamcommunity.com/actions/Search?K=%s" % userid
            page = urllib.urlopen(url)
            if not page:
                raise SteamIDError(
                    "error connecting to the player search page.")

            search = SteamCommunityProfile.rgx_player_search.search(page.read())
            if search is None:
                raise SteamIDError(
                    "name does not exist: http://steamcommunity.com/id/\x02%s\x02/" % userid)

            scurl = search.group(1)
            comm = SteamCommunityProfile.rgx_commid.match(scurl)
            if comm is not None:
                return comm.group(3)

            uid = SteamCommunityProfile.rgx_userid.match(scurl)
            if uid is not None:
                if level < SteamCommunityProfile.MAX_LEVELS_OF_RECURSION:
                    return SteamCommunityProfile.USERID2COMMID(uid.group(3),
                                                               level=level + 1)
                else:
                    raise SteamIDError(
                        'reached maximum level of recursion (%d)' % SteamCommunityProfile.MAX_LEVELS_OF_RECURSION)

            raise SteamIDError(
                "name does not exist: http://steamcommunity.com/id/\x02%s\x02/" % userid)

        return match.group(1)

    @staticmethod
    def input_to_profile(text):
        name = None
        # First check if input is a Steam ID
        match = SteamCommunityProfile.rgx_steamid.match(text)
        if match is not None:
            return SteamCommunityProfile(
                commid=SteamCommunityProfile.STEAMID2COMMID(match))

        # Next we try for a Community ID
        else:
            match = SteamCommunityProfile.rgx_commid.match(text)
            if match is not None:
                return SteamCommunityProfile(commid=match.group(3))

            # And lastly for a URL User ID
            else:
                match = SteamCommunityProfile.rgx_userid.match(text)
                if match is not None:
                    return SteamCommunityProfile(
                        commid=SteamCommunityProfile.USERID2COMMID(
                            match.group(3)))

        return None

    def __init__(self, commid):
        self.commid = long(commid)

        self.name = None
        self.steamid = None
        self.url = None

        self.update_data()

    def __unicode__(self):
        fmt = {
            'steamid': self.steamid,
            'name': self.name,
            'url': self.url,
            'commid': self.commid,
            'commurl': "http://steamcommunity.com/profiles/%d/" % self.commid
        }

        if self.name is None:
            return '%(steamid)s: %(url)s (or %(commurl)s )' % fmt
        elif self.url:
            return '%(name)s (%(steamid)s): %(url)s (or %(commurl)s )' % fmt
        else:
            return '%(name)s (%(steamid)s): %(commurl)s' % fmt

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def update_data(self):
        # Easiest: convert commid to steamid
        self.steamid = SteamCommunityProfile.COMMID2STEAMID(self.commid)

        url = "http://steamcommunity.com/profiles/%d/?xml=1" % self.commid
        try:
            page = urllib.urlopen(url)
        except IOError as e:
            raise SteamIDError(e)

        # Retrieve the profile's name from the URL's XML output
        try:
            xmlpage = urllib.urlopen(url)
        except IOError as e:
            return
        if xmlpage is None:
            return

        try:
            doc = minidom.parse(xmlpage)
        except ExpatError, e:
            raise SteamIDError(e)
        if doc is None:
            return

        for node in doc.firstChild.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE: continue
            if node.nodeName != 'customURL': continue

            if node.firstChild is None or node.firstChild.nodeValue == '':
                self.url = "http://steamcommunity.com/profiles/%d/" % self.commid
            else:
                self.url = 'http://steamcommunity.com/id/%s/' % node.firstChild.nodeValue
            break

        elem = doc.getElementsByTagName("steamID")
        if len(elem) == 0:
            return
        name = elem[0]
        if name == "" or name.firstChild is None:
            return
        self.name = name.firstChild.nodeValue


class SteamID(Plugin):
    @command(aliases=('profile', 'steam'))
    def steamid(self, irc, msg, args):
        """Converts Steam IDs, user IDs, and Community IDs"""
        arg_string = ' '.join(args)
        try:
            profile = SteamCommunityProfile.input_to_profile(arg_string)
        except SteamIDError as e:
            irc.error(str(e))
        else:
            if profile is None:
                irc.error("could not recognize your input.")
            else:
                irc.reply(str(profile))


plugin_class = SteamID
