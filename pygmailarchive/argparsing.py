"""Archive your gmail mailbox to a local directory.  Supports including or excluding
tags, optionally recursively and stores the mails in the same hierarchy as seen via
IMAP. Messages with multiple labels will be fetched into the first folder that
is seen containing them. This means in particular that the "All Mail" folder
will not necessarily contain all messages in case the mails have other labels.
This tool will not download the Spam or Trash folders. It will also not delete mails
locally that have been deleted remotely.

"""

__version__ = "0.3.9"

import argparse
import codecs
import ConfigParser

from config import ENCODING
from util import checkConfigFile, process_list_opt, unicode_decoded

# See main.py for more info on configuring the parser for third-party use.
def get_parser(barebones=False, parents=[]):
    """a configurable parser with optional defaults read from config file
       and parsing of comma-separated include/exclude options into lists
    """

    # common defaults used if not specified in config file or cmdline
    defaults = {
      "username": None,
      "password": None,
      "include": [],
      "exclude": [],
      "archivedir": None,
      "loglevel": "info"
    }

    # third-party users will likely want to use this as a parent parser
    if barebones:
        parser = argparse.ArgumentParser(add_help=False)
    else:
        # parse the config file arg first using a separate parser
        conf_parser = argparse.ArgumentParser(add_help=False)
        cfg_hlp = "Use a ini-format configuration file (command-line args take precedence)"
        conf_parser.add_argument('-c', '--config', metavar ="PATH TO CONFIGURATION FILE",
                                 dest='conf_file', help=cfg_hlp)
        args, leftovers = conf_parser.parse_known_args()

        # update defaults with options read from the config file
        if args.conf_file:
            checkConfigFile(args.conf_file)
            config = ConfigParser.SafeConfigParser()
            config.readfp(codecs.open(args.conf_file, 'r', ENCODING))
            defaults.update(dict(config.items(u"defaults")))
            if defaults[u"include"]:
                defaults[u"include"] = process_list_opt(defaults[u"include"])
            if defaults[u"exclude"]:
                defaults[u"exclude"] = process_list_opt(defaults[u"exclude"])

        conf_parser.set_defaults(**defaults)

        # now, the "real" parser uses conf_parser as parent
        parser_help = (
          "There are two possible usages: either provide the archive directory "
          "(-a/--archivedir), \nor the folder/tag listing command (-f/--folders). "
          "In either case, username & password\nare of course required as well."
        )
        frmt = argparse.RawDescriptionHelpFormatter
        parser = argparse.ArgumentParser(description=__doc__ + parser_help,
                                         formatter_class=frmt, parents=[conf_parser])
        parser.add_argument('-v', '--version', action='version', version=__version__)
        parser.add_argument('-l', '--loglevel', help="one of: INFO|ERROR|WARN|DEBUG")

    # args common to both versions of the parser follow
    auth = parser.add_argument_group("Authentication", "Username & password.")
    auth.add_argument('-p', '--password', dest='password',
                       help='Password to log into Gmail.')
    auth.add_argument('-u', '--username', dest='username',
                       help='Username to log into Gmail.')

    hlp = "Archive chosen folders (tags) to a local maildir++ folder structure"
    arch = parser.add_argument_group("Archival", hlp)
    arch.add_argument('-x', '--exclude', type=unicode_decoded, nargs="+",
                      metavar="FOLDERNAME", help='Exclude given folders/tags.')

    arch.add_argument('-i', '--include', type=unicode_decoded, nargs="+",
                      metavar="FOLDERNAME", help='Include given folders (tags).')
    hlp = (
      "Path of the directory to use for storing the downloaded imap folders and"
      "pygmailarchive metadata."
    )
    arch.add_argument('-a', '--archivedir', metavar="PATH", help=hlp)
    lst = parser.add_argument_group("Folder/tag listing",
      "Don't archive, just list all message folder (tag) names"
    )
    lst.add_argument('-f', '--list_folders', action="store_true", help='List folders.')

    # while it's undocumented, at least the current version of argparse supports repeat
    # reads of the args, despite parse_known_args having been called already; so the
    # parser can be used normally
    return parser

