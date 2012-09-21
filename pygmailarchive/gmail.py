import imapclient
from contextlib import contextmanager


@contextmanager
def gmail(username, password, ssl=True):
    imapcon = imapclient.IMAPClient("imap.gmail.com", ssl=ssl)
    # Fetch datetime info with timezone info
    imapcon.normalise_times = False
    imapcon.login(username, password)
    yield imapcon
    imapcon.logout()


def checkIMAPFolders(includes, excludes, all_folders, foldersep):
    "stop on invalid folder names"
    root_folders = [fname.split(foldersep)[0] for fname in all_folders]
    invalids = [fname for fname in (includes + excludes) if fname not in root_folders]
    if invalids:
       raise Exception("One or more invalid folder names given: %s" % ', '.join(invalids))


