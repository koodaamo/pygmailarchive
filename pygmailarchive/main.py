#!/usr/bin/env python

import sys
import math
import getpass
import mailbox
import logging

from argparsing import get_parser
from util import gmail, makeFSCompatible, mailfolder
from config import logger

# if you use this from third-party software, pass a list of parents to apply and a logger

def run_archiver(parents=[], logger=logger):

    # if we're given parents, third-party sw wants to mix with the barebones parser
    bbones = True if parents else False
    argparser = get_parser(parents=parents, barebones=bbones)
    args = argparser.parse_args()

    loglevel= getattr(logging, args.loglevel.upper())
    logger.setLevel(loglevel)

    # Require either archival or listing operation before proceeding.
    if not (args.list_folders or args.archivedir):
        argparser.print_help()
        sys.exit()

    # Auth & connect
    username = args.username or raw_input("Username: ")
    password = args.password or getpass.getpass()
    with gmail(username, password) as imapcon:
       logger.info("Connected")

       # Get folder listing and folder path separator from server; they will be needed.
       # Also make a slash ('/') -delimited list of all folders for convenience.
       # Note: an IMAP folder entry contains the full path, not just the leaf.
       folders = [fdata[2] for fdata in imapcon.list_folders()]
       fsep = imapcon.namespace().personal[0][1]
       folders_slashdelimited = [fname.replace(fsep, u'/') for fname in folders]

       # If requested (-f/--folders), just output it & exit
       if args.list_folders:
          sys.exit("Folders on server: %s" % ", ".join(folders_slashdelimited))

       # Apply include/exclude options on the list of folders found on server, after
       # making sure they exist on server.
       invalids = []
       if args.include:
           invalids += [fld for fld in args.include if fld not in folders_slashdelimited]
       if args.exclude:
           invalids += [fld for fld in args.exclude if fld not in folders_slashdelimited]
       if invalids:
           sys.exit("Invalid include/exclude folder names: '%s'" % invalids)
       folders = args.include or (set(folders_slashdelimited) - set(args.exclude))

       # Archive messages!
       logger.info("Archiving '%s' to %s" % ("', '".join(folders), args.archivedir))
       archive = mailbox.Maildir(args.archivedir)
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

           parts = [makeFSCompatible(unicode(prt)) for prt in foldername.split(fsep)]
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


