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
import math
import os
import getpass
import mailbox


from ConfigParser import SafeConfigParser
from pygmailarchive.argparsing import parser
from pygmailarchive.util import gmail, logger, makeFSCompatible, mailfolder
from pygmailarchive.config import getconfig, FOLDERLIST_CMD


def main():

    # COMMAND-LINE ARGS & CONFIG FILE
    argparser = parser()
    args = argparser.parse_args()
    cfg = SafeConfigParser()

    # get the configuration
    cmd, user, passwd, includes, excludes, archivedir, loglevel = getconfig(args, cfg)

    includes = includes or []
    excludes = excludes or []

    if loglevel:
        logger.setLevel(loglevel)

    # Require either archival or listing operation before proceeding.
    if not cmd:
        argparser.print_help()
        sys.exit()

    # Auth & connect
    username = user or raw_input("Username: ")
    password = passwd or getpass.getpass()

    with gmail(username, password) as imapcon:

       logger.info("Connected")
       # Get folder listing first
       all_folders = [fdata[2] for fdata in imapcon.list_folders()]

       # If requested (-f/--folders), just output it & exit
       if cmd == FOLDERLIST_CMD:
          sys.exit("Folders on server: %s" % " ".join(all_folders))

       # Parse, check and apply folder constraints given by user.
       # Constraints are given using '/' as the folder path separator
       fldrsep = imapcon.namespace().personal[0][1]
       fixsep = lambda pths: [unicode(pth.replace('/', fldrsep)) for pth in pths]

       if includes or excludes:
           inv_inc = [f for f in fixsep(includes) if f not in all_folders]
           inv_exc = [f for f in fixsep(excludes) if f not in all_folders]
           invalids = "' and '".join(inv_inc + inv_exc)
           if invalids:
              sys.exit("Invalid include/exclude folder names: '%s'" % invalids)

       folders = includes or [f for f in all_folders if f not in excludes]
       logger.info("Archiving: %s" % ", ".join(folders))

       # Ok. Set up the archive dir.
       archive = mailbox.Maildir(archivedir)

       # Archive messages!
       for foldername in folders:
           select_info = imapcon.select_folder(foldername)
           if select_info['EXISTS'] == 0:
               logger.info("Folder %s: no messages!" % foldername)
               continue

           uids = imapcon.fetch("1:%s" % select_info['EXISTS'], ['UID',])
           logger.info("Folder %s: %i messages on server" % (foldername, len(uids)))
           logger.debug("... fetching uids for 1-%s" %(select_info['EXISTS'],))

           uidvalidity = select_info['UIDVALIDITY']
           logger.debug("... UID validity: %s" % uidvalidity)

           parts = [makeFSCompatible(unicode(prt)) for prt in foldername.split(fldrsep)]
           fsname = '.'.join(parts)

           with mailfolder(archive, fsname) as (folder, cached_uid_info):
               newuids = [id for id in uids if ((uidvalidity, id) not in cached_uid_info)]
               oldcount, newcount = len(cached_uid_info), len(newuids)
               logger.info("... %i archived messages, %i new" % (oldcount, newcount))

               # use batched logging
               fetched = []
               interval = 1
               if len(newuids) > 100:
                   interval = int(math.sqrt(len(newuids)))
                   logger.warn("... using batched logging (entry per %i msgs)" % interval)

               for i, uid in enumerate(newuids):
                   fetch_info = imapcon.fetch(uid, ["BODY.PEEK[]",])
                   logger.debug("... info: %s" % fetch_info)
                   msg = fetch_info[uid]["BODY[]"]

                   # If a message cannot be stored, skip it instead of failing
                   try:
                       folder.add(msg)
                       cached_uid_info.append((uidvalidity,uid))
                   except Exception, e:
                       logger.error("... error storing mail: %s\n%s" %(msg,e), False)

                   fetched.append(str(uid))
                   if not (i % interval):
                       logger.info("... got message(s): %s" % ", ".join(fetched))
                       fetched = []

if __name__ == '__main__':
    main()
