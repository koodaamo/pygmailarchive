import os
import stat
import string
import re
import logging
import unicodedata
import imapclient
from contextlib import contextmanager

#from config import SEENMAILS_FILENAME, LOG_FORMAT, LOG_DATEFORMAT

LOG_FORMAT = "[%(asctime)s]: %(message)s"
LOG_DATEFORMAT = '%H:%M:%S'
SEENMAILS_FILENAME = "pygmailarchive.seenmails"


logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
logger=logging.getLogger("gmailarchive")


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

