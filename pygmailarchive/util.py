import os
import stat
import ConfigParser
import imapclient
import string
import re
import unicodedata
from contextlib import contextmanager


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
        cfg.read(cfgfile)
    except ConfigParser.MissingSectionHeaderError:
        raise Exception("Config file has no sections. It needs to have [authentication] and/or [archival] section.")

    if not set(cfg.sections()).issubset(("authentication", "archival")):
        raise Exception("Invalid config file sections given. Provide [authentication] and/or [archival] section(s).")

    all_options = cfg.options("authentication") + cfg.options("archival")
    if not set(all_options).issubset(("username", "password", "includes", "excludes", "archivedir")):
        raise Exception("One or more invalid config file options given. Check your config file.")


def checkIMAPFolders(includes, excludes, all_folders, foldersep):
    "stop on invalid folder names"
    root_folders = [fname.split(foldersep)[0] for fname in all_folders]
    invalids = [fname for fname in (includes + excludes) if fname not in root_folders]
    if invalids:
       raise Exception("One or more invalid folder names given: %s" % ', '.join(invalids))


def makeFSCompatible(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')
    valid_chars_re = '[^-_.()\[\]{} %s%s]' %(string.ascii_letters, string.digits)
    return unicode(re.sub(valid_chars_re, '_', name))


