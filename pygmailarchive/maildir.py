import os
import mailbox
from contextlib import contextmanager

from pygmailarchive.util import makeFSCompatible

SEENMAILS_FILENAME = "pygmailarchive.seenmails"


@contextmanager
def maildir(archivedir, foldername, foldersep):

    fsfoldername = [makeFSCompatible(fname) for fname in foldername.split(foldersep)]
    mdpath = os.path.join(archivedir, fsfoldername[0])

    # Create maildir
    md = mailbox.Maildir(mdpath)
    for folder in fsfoldername[1:]:
        md = md.add_folder(folder)

    # Read a seenmails-file containing identifiers for the mails that were downloaded already
    seenMailsFile = os.path.join(mdpath, SEENMAILS_FILENAME)
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

    yield (md, seenMailIds)

    # write seen emails
    seenFile = open(os.path.join(mdpath, SEENMAILS_FILENAME), "w")
    for (uidvalidity,uid) in seenMailIds:
        seenFile.write("%s\0%s\n" %(uidvalidity, uid))
    seenFile.close()
