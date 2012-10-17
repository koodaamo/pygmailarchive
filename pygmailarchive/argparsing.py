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
import logging


def get_parent_parser():
    "make a parent parser that can also be used in third-party apps"
    parent = argparse.ArgumentParser(add_help=False)
    auth = parent.add_argument_group("Authentication", "Username & password.")
    auth.add_argument('-p', '--password', dest='password',
      help='Password to log into Gmail.')
    auth.add_argument('-u', '--username', dest='username',
      help='Username to log into Gmail.')

    hlp = "Archive chosen folders/tags to a local maildir++ folder structure"
    arch = parent.add_argument_group("Archival", hlp)
    arch.add_argument('-x', '--exclude', nargs="+", dest='excludes',
      help='Exclude given tags.'
    )
    arch.add_argument('-i', '--include', nargs="+", dest='includes',
      help='Include given tags.'
    )
    hlp = (
      "Path to a directory to use for storing the downloaded imap folders and"
      "pygmailarchive metadata."
    )
    arch.add_argument('-a', '--archivedir', help=hlp)
    lst = parent.add_argument_group("Folder/tag listing",
      "Don't archive, just list all message tag (folder) names"
    )
    lst.add_argument('-f', '--folders', action="store_true", help='List all folders.')

    return parent


def get_parser():
    "build the argument parser"

    hlp = (
      "There are two possible usages: either provide the archive directory "
      "(-a/--archivedir), \nor the folder/tag listing command (-f/--folders). "
      "In either case, username & password\nare of course required as well."
    )
    frmt = argparse.RawDescriptionHelpFormatter
    parent = get_parent_parser()
    parser = argparse.ArgumentParser(description=__doc__ + hlp, formatter_class=frmt,
                                     parents=[parent])

    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-l', '--loglevel', default=logging.INFO,
                        help="Log level; INFO, ERROR, WARN or DEBUG")

    conf = parser.add_argument_group("Configuration file",
                                     "Settings can be read from a config file as well.")

    hlp = "Config file must be ini-formatted. Command-line args override config file."
    conf.add_argument('-c', '--config', dest='cfgfile', help=hlp)

    return parser
