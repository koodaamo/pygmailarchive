import os
import stat
import sys
import string
import re
import codecs
import unicodedata
import imapclient
import ConfigParser
from contextlib import contextmanager

from config import ENCODING, SEENMAILS_FILENAME

# used in arg parser to convert values using 'type=unicode_decoded'
unicode_decoded = lambda x: x.decode(sys.stdin.encoding)

# used below in process_list_opt
stripsplit = lambda opt: opt.strip().strip(',').strip().split(",")

def process_list_opt(opt):
    "split comma-separated 'list' option into a tuple"
    if ',' in opt:
       return [item.strip() for item in stripsplit(opt)]
    else:
      return [opt]


def checkConfigFile(cfgfile):
    "check the file"

    if not os.path.exists(cfgfile):
       raise Exception("Non-existing config file specified: '%s'" % (cfgfile,))
    status = os.stat(cfgfile)
    mode = status.st_mode
    if not stat.S_ISREG(mode):
       raise Exception("Config filename does not point to a regular file: '%s'" %(cfgfile,))
    if not os.access(cfgfile, os.R_OK):
        raise Exception("Config file '%s' is not readable by current user" %(cfgfile,))
    if not isUserReadWritableOnly(mode):
        raise Exception("Config file '%s' is readable by other users, possible security problem, aborting" %(cfgfile,))

    cfg = ConfigParser.SafeConfigParser()
    try:
        cfg.readfp(codecs.open(cfgfile, 'r', ENCODING))
    except ConfigParser.MissingSectionHeaderError:
        raise Exception("Config file has no sections. It needs to have a [defaults] section.")

    if not cfg.sections() == ["defaults"]:
        raise Exception("Only a [defaults] section allowed. Check your config file.")

    all_options = ("username", "password", "include", "exclude", "archivedir", "loglevel")

    if not set(cfg.options("defaults")).issubset(all_options):
        raise Exception("One or more invalid options given. Check your config file.")


@contextmanager
def gmail(username, password, ssl=True):
    imapcon = imapclient.IMAPClient("imap.gmail.com", ssl=ssl)
    # Fetch datetime info with timezone info
    imapcon.normalise_times = False
    imapcon.login(username, password)
    yield imapcon
    imapcon.logout()


def isUserReadWritableOnly(mode):
    return bool(stat.S_IRUSR & mode) and not (
            bool(stat.S_IXUSR & mode) or
            bool(stat.S_IRGRP & mode) or
            bool(stat.S_IWGRP & mode) or
            bool(stat.S_IXGRP & mode) or
            bool(stat.S_IROTH & mode) or
            bool(stat.S_IWOTH & mode) or
            bool(stat.S_IXOTH & mode) )


def makeFSCompatible(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')
    valid_chars_re = '[^-_()\[\]{} %s%s]' %(string.ascii_letters, string.digits)
    return unicode(re.sub(valid_chars_re, '_', name))


@contextmanager
def mailfolder(archive, foldername):
    md = archive.add_folder(foldername)

    # Read a seenmails-file containing identifiers for the mails downloaded already
    seenMailsPath = md._path + os.sep + SEENMAILS_FILENAME
    UIDInfos = []
    if os.path.exists(seenMailsPath):
        with open(seenMailsPath, "rb") as seenFile:
            UIDInfos = [line.strip().split('\0') for line in seenFile]
            UIDInfos = [(int(v), int(u)) for v, u in UIDInfos]
    else:
        UIDInfos=[]

    yield (md, UIDInfos)

    # write seen emails back to the UID info cache file
    with open(seenMailsPath, "w") as seenFile:
        for (uidvalidity,uid) in UIDInfos:
            seenFile.write("%i\0%i\n" %(uidvalidity, uid))

