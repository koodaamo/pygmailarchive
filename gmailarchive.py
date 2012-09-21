
#!/usr/bin/env python

"""Archive your gmail mailbox to a local directory.  Supports excluding tags,
optionally recursively and stores the mails in the same hierarchy as seen via
IMAP. Messages with multiple labels will be fetched into the first folder that
is seen containing them. This means in particular that the "All Mail" folder
will not necessarily contain all messages in case the mails have other labels.
This tool will not download the Spam or Trash folders at the moment.
This tool will not delete mails locally that have been deleted remotely.
"""

import sys
import os
import getpass
import logging
import ConfigParser

from pygmailarchive.argparsing import parser
from pygmailarchive.maildir import maildir
from pygmailarchive.util import gmail, checkIMAPFolders, checkConfigFile

FORMAT = "[%(asctime)s]: %(message)s"
DATEFORMAT = '%H:%M:%S'
logging.basicConfig(level=logging.WARN, format=FORMAT, datefmt=DATEFORMAT)
logger=logging.getLogger("gmailarchive")
log=logger.info


def main():

    argparser = parser()
    args = argparser.parse_args()
    logger.debug("Arguments: %s" %(args,))

    # If a config file was passed, check & read it
    cfg = ConfigParser.SafeConfigParser()
    if args.cfgfile:
        checkConfigFile(args.cfgfile)
        try:
           cfg.read(args.cfgfile)
        except ConfigParser.MissingSectionHeaderError:
           raise Exception("Config file needs to have [authentication] and/or [archival] section")

    # Options in config file are overriden by command-line args, if given
    # Here's a convenience to get the possibly overriden option
    var = lambda s, o: getattr(args, o, None) or cfg.get(s, o)

    if args.loglevel:
        logger.setLevel(args.loglevel)

    # Require either archival or listing operation before proceeding.
    archivedir = var("archival", "archivedir")
    if not (archivedir or args.list):
        argparser.print_help()
        sys.exit()

    # Auth & connect
    username = var("authentication", "username") or raw_input("Username: ")
    password = var("authentication", "password") or getpass.getpass()

    with gmail(username, password) as imapcon:

       # If the folder listing (-f/--folders) command was given
       if args.folders:
          print "\n".join([d[2] for d in imapcon.list_folders()])
          sys.exit()

       # Otherwise, we're archiving the folders:
       # Make sure the directory exists first
       if not os.path.isabs(archivedir):
           archivedir = os.path.join(os.getcwd(), archivedir)
       if not os.path.exists(archivedir):
           os.makedirs(archivedir)

       # get the 'personal namespace separator' (folder path separator, usually '/')
       foldersep = imapcon.namespace().personal[0][1]

       # stop on invalid folder names
       includes = var("archival", "includes")
       excludes = var("archival", "excludes")
       includes = includes.split(",") if includes else []
       excludes = excludes.split(",") if excludes else []

       all_folders = [fdata[2] for fdata in imapcon.list_folders()]
       checkIMAPFolders(includes, excludes, all_folders, foldersep)

       # folder selection based on user input
       if includes :
           folders = [fname for fname in all_folders if fname in includes]
           mode = "including %s" % ", ".join(folders)
       elif excludes:
           folders = set(all_folders) - set([fname for fname in all_folders if fname in excludes])
           mode = "excluding %s" % ", ".join(excludes)
       else:
           mode = "getting all folders"
           folders = all_folders
       logger.info("Archiving mails, %s folder(s)..." % mode)

       for foldername in folders:
           with maildir(archivedir, foldername, foldersep) as (targetmd, seen_mails):
               if seen_mails:
                   logger.info("Cache has %i messages" % len(seen_mails))
               select_info = imapcon.select_folder(foldername)
               uidvalidity = select_info['UIDVALIDITY']
               logger.info("Fetching mail ids for: 1-%s" %(select_info['EXISTS'],))
               if select_info['EXISTS'] > 0:
                   uids = imapcon.fetch("1:%s" %(select_info['EXISTS'],), ['UID',])
                   for uid in uids:
                       if not (uidvalidity,uid) in seen_mails:
                           logger.info("Fetching Mail: %s" %(uid,))
                           fetch_info = imapcon.fetch(uid, ["BODY.PEEK[]",])
                           logger.info("Fetched Info for uid %s: %s" %(uid, fetch_info))
                           msg = fetch_info[uid]["BODY[]"]
                           logger.debug("Got Mail Message: %s" %(msg,))

                           # If a message cannot be stored, skip it instead of failing completely
                           try:
                               targetmd.add(msg)
                               seen_mails.append((uidvalidity,uid))
                           except Exception, e:
                               logger.error("Error storing mail: %s\n%s" %(msg,e), False)
                       else:
                           logger.info("Already fetched: %s" % uid)



if __name__ == '__main__':
    main()
