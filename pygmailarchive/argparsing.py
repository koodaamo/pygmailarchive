"""Archive your gmail mailbox to a local directory.  Supports excluding tags,
optionally recursively and stores the mails in the same hierarchy as seen via
IMAP. Messages with multiple labels will be fetched into the first folder that
is seen containing them. This means in particular that the "All Mail" folder
will not necessarily contain all messages in case the mails have other labels.
This tool will not download the Spam or Trash folders at the moment.
This tool will not delete mails locally that have been deleted remotely.
"""

__version__ = "0.3.9"

import argparse
import logging

def parser():
    "build the argument parser"

    parser = argparse.ArgumentParser(
        description=__doc__ + "Provide username & password, and either the archive directory (-a/--archivedir), or use the folder/tag listing command (-f/--folders)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('-v', '--version', action='version', version=__version__)

    parser.add_argument('-l', '--loglevel', default=logging.INFO, help="Log level; INFO, ERROR, WARN or DEBUG")

    conf = parser.add_argument_group("Configuration file", "Settings can alternatively be read from a config file.")
    conf.add_argument('-c', '--config', dest='cfgfile', help="Config file must be ini-formatted. Command-line parameters override those in config file.")

    auth = parser.add_argument_group("Authentication", "Username & password.")
    auth.add_argument('-p', '--password', dest='password', help='Password to log into Gmail.')
    auth.add_argument('-u', '--username', dest='username', help='Username to log into Gmail.')

    archival = parser.add_argument_group("Archival", "Archive messages from chosen folders (tags) to a local maildir folder structure")
    archival.add_argument('-x', '--exclude', nargs="+", dest='excludes', help='Exclude the given tags.')
    archival.add_argument('-i', '--include', nargs="+", dest='includes', help='Include the given tags.')
    archival.add_argument('-a', '--archivedir', help='Path to a directory to use for storing the downloaded imap folders and pygmailarchive metadata.')

    listing = parser.add_argument_group("Folder/tag listing", "Don't archive, just list all message tag (folder) names")
    listing.add_argument('-f', '--folders', action="store_true", help='List all folders.')

    return parser
