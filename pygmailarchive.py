
#!/usr/bin/env python

"""Archive your gmail mailbox to a local directory.  Supports excluding tags,
optionally recursively and stores the mails in the same hierarchy as seen via
IMAP. Messages with multiple labels will be fetched into the first folder that
is seen containing them. This means in particular that the "All Mail" folder
will not necessarily contain all messages in case the mails have other labels.
This tool will not download the Spam or Trash folders at the moment.
This tool will not delete mails locally that have been deleted remotely.
"""
# Separate doc-comment for the license so its not part of the --help output
"""
Copyright (c) 2012, Andreas Pakulat <apaku@gmx.de>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

#TODO: Improve handling of mails in folders and in All Mail
#TODO: Optionally download spam and/or trash

__version__ = '0.3.0'

import email
import email.Header
import email.Utils
import os
import stat
import sys
import time
import argparse
import ConfigParser
import imapclient
import getpass
import string
import re
import unicodedata
import mailbox
import logging


FORMAT = "[%(asctime)s]: %(message)s"
DATEFORMAT = '%H:%M:%S'
logging.basicConfig(level=logging.WARN, format=FORMAT, datefmt=DATEFORMAT)
log=logging.info

SEENMAILS_FILENAME = "pygmailarchive.seenmails"


def isUserReadWritableOnly(mode):
    return bool(stat.S_IRUSR & mode) and not (
            bool(stat.S_IXUSR & mode) or
            bool(stat.S_IRGRP & mode) or
            bool(stat.S_IWGRP & mode) or
            bool(stat.S_IXGRP & mode) or
            bool(stat.S_IROTH & mode) or
            bool(stat.S_IWOTH & mode) or
            bool(stat.S_IXOTH & mode) )

def checkConfig(configfile):
    if configfile is not None:
        if not os.path.exists(configfile):
            raise Exception("Non-existing config file specified: '%s'" % (configfile,))
        status = os.stat(configfile)
        mode = status.st_mode
        if not stat.S_ISREG(mode):
            raise Exception("Config filename does not point to a regular file: '%s'" %(configfile,))
        if not os.access(configfile, os.R_OK):
            raise Exception("Config file '%s' is not readable by current user" %(configfile,))
        if not isUserReadWritableOnly(mode):
            raise Exception("Config file '%s' is readable by other users, possible security problem, aborting" %(configfile,))
        config = ConfigParser.SafeConfigParser()
       
        try:
           config.read(configfile)
        except ConfigParser.MissingSectionHeaderError:
            raise Exception("Config file needs to have either [authentication] or [archival] section, or both.")


def readConfig(config, opts):
    "read configuration file into options"
    for section, option in opts.items():
       try:
          opts[section][option] = config.get(section, option)
       except:
          pass

def readArgs(opts, args):
    "read cmdline args into options"
    for section in opts:
        for opt in opts[section]:
            if hasattr(args, opt):
                opts[section][opt] = getattr(args, opt)

def checkFolders(includes, excludes, all_folders, foldersep):
    "stop on invalid folder names"
    root_folders = [fname.split(foldersep)[0] for fname in all_folders]
    invalids = [fname for fname in (includes + excludes) if fname not in root_folders]
    if invalids:
       raise Exception("One or more invalid folder names given: %s" % ', '.join(invalids))


def readCredentials(opts):
    username = opts["authentication"]["username"] or raw_input("Username: ")
    password = opts["authentication"]["password"] or getpass.getpass()
    return (username, password)


def connectToGMail(username, password):
    imapcon = imapclient.IMAPClient("imap.gmail.com", ssl=True)
    # Fetch datetime info with timezone info
    imapcon.normalise_times = False
    imapcon.login(username, password)
    log("Logged in on imap.gmail.com, capabilities: %s" %(imapcon.capabilities(),), False)
    return imapcon

def disconnectFromGMail(imapcon):
    log("Logging out from imap.gmail.com", False)
    imapcon.logout()

def setupArchiveDir(archivedir):
    if not os.path.isabs(archivedir):
        archivedir = os.path.join(os.getcwd(), archivedir)
    if not os.path.exists(archivedir):
        os.makedirs(archivedir)
    return archivedir

def makeFSCompatible(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')
    valid_chars_re = '[^-_.()\[\]{} %s%s]' %(string.ascii_letters, string.digits)
    return unicode(re.sub(valid_chars_re, '_', name))

def createMaildirs(destination, fsfoldername):
    abspath = os.path.join(destination, fsfoldername[0])
    md = mailbox.Maildir(abspath)
    for folder in fsfoldername[1:]:
        md = md.add_folder(folder)
    return md

def readSeenMails(maildirfolder):
    # Reads a seenmails-file containing identifiers for the mails that were downloaded already
    # The file format is rather simple: each line contains the uidvalidity and the uid for a given
    # message
    seenMailsFile = os.path.join(maildirfolder, SEENMAILS_FILENAME)
    seenMailIds = []
    if os.path.exists(seenMailsFile):
        seenFile = open(seenMailsFile)
        try:
            for line in seenFile.readlines():
                data = line.split('\0')
                if len(data) != 2:
                    raise Exception("Error, invalid line: '%s' in seenmails file: '%s'" %(line, seenMailsFile))
                # Each line is composed of uidvalidity and uid forming a unique identifier
                seenMailIds.append((int(data[0]), int(data[1])))
        finally:
            seenFile.close()
    return seenMailIds

def fetchMail(imapcon, uid):
    # Using messages as strings here for performance reasons, no point in converting them to email.Message.Message or
    # a mailbox.Message instance, since the mailboxes can write out plain-string-emails too.
    fetch_info = imapcon.fetch(uid, ["BODY.PEEK[]",])
    log("Fetched Info for uid %s: %s" %(uid, fetch_info))
    msgstring = fetch_info[uid]["BODY[]"]
    return msgstring

def storeMessage(maildir, msg):
    maildir.add(msg)

def writeSeenMails(maildirfolder, seen_mails):
    if not os.path.exists(maildirfolder):
        raise Exception("Cannot write seen-mails file, folder '%s' does not exist" %(maildirfolder,))
    seenFile = open(os.path.join(maildirfolder, SEENMAILS_FILENAME), "w")
    for (uidvalidity,uid) in seen_mails:
        seenFile.write("%s\0%s\n" %(uidvalidity, uid))
    seenFile.close()

def archiveMails(imapcon, destination, excludes, includes):
   
    all_folders = [fdata[2] for fdata in imapcon.list_folders()]
    # get the personal namespace (folder path) separator
    foldersep = imapcon.namespace().personal[0][1]
    # stop on invalid folder names
    checkFolders(includes, excludes, all_folders, foldersep)

    # folder selection - inclusive mode
    if includes :
        folders = [fname for fname in all_folders if fname in includes]
        mode = "including %s" % ", ".join(folders)
    # folder selection -exclusive mode
    elif excludes:
        # subtraction does not work on tuples or lists
        folders = set(all_folders) - set([fname for fname in all_folders if fname in excludes])        
        mode = "excluding %s" % ", ".join(excludes)
    # neither, get everything
    else:
        mode = "getting all folders"
        folders = all_folders
       
    log("Archiving mails, %s" % mode)

    for foldername in folders:
         fsfoldername = [makeFSCompatible(fname) for fname in foldername.split(foldersep)]
         # Create the mailboxes
         targetmd = createMaildirs(destination, fsfoldername)
         log("Using local maildir: %s - %s" %(fsfoldername,targetmd._path), False)
         # Its not nice to access private attributes, but unfortunately there's no API at the moment
         # which supplies the filesystem path that we need
         seen_mails = readSeenMails(targetmd._path)
         select_info = imapcon.select_folder(foldername)
         uidvalidity = select_info['UIDVALIDITY']
         log("Fetching mail ids for: 1-%s" %(select_info['EXISTS'],))
         if select_info['EXISTS'] > 0:
             uids = imapcon.fetch("1:%s" %(select_info['EXISTS'],), ['UID',])
             for uid in uids:
                 if not (uidvalidity,uid) in seen_mails:
                     log("Fetching Mail: %s" %(uid,))
                     msg = fetchMail(imapcon, uid)
                     log("Got Mail Message: %s" %(msg,))
                     # If a message cannot be stored, skip it instead of failing completely
                     try:
                         storeMessage(targetmd, msg)
                         seen_mails.append((uidvalidity,uid))
                     except Exception, e:
                         log("Error storing mail: %s\n%s" %(msg,e), False)
             writeSeenMails(targetmd._path, seen_mails)

def main():
    parser = argparse.ArgumentParser(
        description=__doc__ + "At minimum, you must provide username & password, and either the archive directory (-a/--archivedir), or use the folder/tag listing command (-l/--list)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('-v', '--version', action='version',
        version=__version__)

    conf = parser.add_argument_group("Configuration file", "Settings can alternatively be read from a config file.")
    conf.add_argument('-c', '--config', dest='configfile',
        help="Name of the (ini-formatted) config file specifying command options. If a config file is used, command-line parameters are ignored.")

    auth = parser.add_argument_group("Authentication", "Username & password.")
    auth.add_argument('-p', '--password', dest='password',
        help='Password to log into Gmail.')
    auth.add_argument('-u', '--username', dest='username',
        help='Username to log into Gmail.')

    archival = parser.add_argument_group("Archival", "Archive messages from chosen folders (tags) to a local maildir folder structure")
    archival.add_argument('-x', '--exclude', metavar="TAG", nargs="+", action='append', dest='excludes', default=[],
        help='Exclude the given tags.')
    archival.add_argument('-i', '--include', metavar="TAG", nargs="+", dest='includes',
        help='Include the given tags.')
    archival.add_argument('-a', '--archivedir',
        help='Set the directory where to store the downloaded imap folders. Will also contain metadata to avoid re-downloading all files.')

    listing = parser.add_argument_group("Folder/tag listing", "Don't archive, just list all message tag (folder) names")
    listing.add_argument('-l', '--list', action="store_true", help='List all folders.')

    args = parser.parse_args()
    log("Arguments: %s" %(args,))

    # Require either archival or listing operation
    if not (args.archivedir or args.list):
        parser.print_help()
        sys.exit()

    # Options read from both config & cmdline args (the latter override if both are present)
    opts = {"authentication": {"username":None, "password":None},
            "archival": {"includes":[], "excludes":[], "archivedir":None}
    }
    # A config file was passed, read it
    if args.configfile:
        config = checkConfig(args.configfile)
        readConfig(opts, config)
    # Apply overrides from args
    readArgs(opts, args)    
    
    # Authenticate & connect
    (username, password) = readCredentials(opts)
    imapcon = connectToGMail(username, password)

    # If the listing (-l/--list) command was given
    if args.list:
       print "\n".join([d[2] for d in imapcon.list_folders()])
       sys.exit()

    # Otherwise, we're archiving the folders
    archivedir = setupArchiveDir(args.archivedir)
    try:
        archiveMails(imapcon, archivedir, includes=args.includes, excludes=args.excludes)
    finally:
        disconnectFromGMail(imapcon)


if __name__ == '__main__':
    main()
