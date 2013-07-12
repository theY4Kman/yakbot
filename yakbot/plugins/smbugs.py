from datetime import datetime
import re
from urllib2 import urlopen
from xml.dom import minidom

from yakbot.ext import Plugin, command


class InvalidBug(Exception):
    pass


class BugXML(object):
    RGX_TZ_OFFS = re.compile(r'\s*-\d{4}$')

    def __init__(self, bug_id):
        self.bug_id = bug_id
        self.url = self._make_url(self.bug_id)

        self.xml_url = self._make_xml_url(self.bug_id)
        page = self._retrieve_page(self.xml_url)
        self.doc = self._parse_doc(page)

        try:
            bug_elem = self.doc.getElementsByTagName('bug')[0]
        except IndexError:
            raise InvalidBug('Could not find <bug> tag')

        if not bug_elem.attributes:
            return

        try:
            bug_elem.attributes['error']
        except KeyError:
            pass
        else:
            error = bug_elem.attributes['error'].value
            raise InvalidBug(error)

    def _make_xml_url(self, bug_id):
        return 'https://bugs.alliedmods.net/show_bug.cgi?ctype=xml&id=%s' % bug_id

    def _make_url(self, bug_id):
        return 'https://bugs.alliedmods.net/show_bug.cgi?id=%s' % bug_id

    def _retrieve_page(self, url):
        return urlopen(url)

    def _parse_doc(self, page):
        return minidom.parse(page)

    @staticmethod
    def get_tag_text(root, tag_name):
        elements = root.getElementsByTagName(tag_name)
        element = elements[0]
        text_node = element.firstChild
        return text_node.nodeValue

    @staticmethod
    def get_tag_text_and_attrs(root, tag_name):
        elements = root.getElementsByTagName(tag_name)
        element = elements[0]
        text_node = element.firstChild
        text = text_node.nodeValue
        attrs = dict(element.attributes.items())
        return text, attrs

    def get(self, tag_name):
        """Returns inner text of the first tag with the specified name."""
        return self.get_tag_text(self.doc, tag_name)
    __getitem__ = get

    def get_comments(self):
        """Returns a list of dicts describing the comments"""
        elements = self.doc.getElementsByTagName('long_desc')

        comments = []
        for element in elements:
            get_text = lambda n: self.get_tag_text(element, n)
            comment = dict((n, get_text(n)) for n in ('commentid', 'bug_when',
                                                      'thetext'))

            bug_when = comment['bug_when']
            bug_when = self.RGX_TZ_OFFS.sub('', bug_when, 1)
            comment['bug_when'] = datetime.strptime(bug_when,
                                                    '%Y-%m-%d %H:%M:%S')

            username, attrs = self.get_tag_text_and_attrs(element, 'who')
            comment['username'] = username
            comment['display_name'] = attrs['name']

            comments.append(comment)

        return comments


class SMBugs(Plugin):
    @command
    def bug(self, irc, msg, args):
        """Look up a bug on bugs.alliedmods.net"""
        try:
            bug_id = int(args[0])
        except ValueError:
            irc.error('Invalid bug ID "\x02%s\x02"' % args[0])
            return

        try:
            bug = BugXML(bug_id)
        except InvalidBug as e:
            irc.error('Error processing bug: ' + str(e))
            return

        notable_tags = ('product', 'component', 'version', 'bug_status',
                        'priority', 'bug_severity', 'short_desc')
        context = dict((k, bug[k]) for k in notable_tags)
        context['id'] = bug_id
        context['url'] = bug.url

        assn_user, attrs = bug.get_tag_text_and_attrs(bug.doc, 'assigned_to')
        assn_dispname = attrs['name']
        context['assn_user'] = assn_user
        context['assn_dispname'] = assn_dispname

        comments = bug.get_comments()
        context['num_comments'] = len(comments)
        context['num_comments_plural'] = '' if len(comments) == 1 else 's'

        fmt = ('#%(id)d [%(product)s]: %(short_desc)s '
               '[%(num_comments)s comment%(num_comments_plural)s] ( %(url)s )')
        irc.reply((fmt % context).encode('ascii', 'replace'))


plugin_class = SMBugs
