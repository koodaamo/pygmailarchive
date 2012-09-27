import os
import stat
import ConfigParser
import sys

from util import isUserReadWritableOnly

ARCHIVE_CMD = 1
FOLDERLIST_CMD = 2


def arg_or_cfg(args, cfg):
    "return arg or conf value (as unicode), or None"
    def opt(s, o, args=args, cfg=cfg):
        if getattr(args, o, False):
            optval = getattr(args, o)
        else:
            try:
                optval = cfg.get(s,o)
            except:
                return None
        if type(optval) == str:
           return optval.decode("utf-8")
        elif type(optval) == list:
           return [v.decode("utf-8") for v in optval]
        else:
           raise Exception("%s not valid for option type" % type(optval))
    return opt


def getconfig(args, cfg):
    "combine cmdline and config file opts together"

    # CONFIG FILE
    if args.cfgfile:
        checkConfigFile(args.cfgfile)
        cfg.read(args.cfgfile)

    # Options in config file are overriden by command-line args, if given.
    # We're using a partial to get the possibly overriden option in one call.
    opt = arg_or_cfg(args, cfg)

    # username & password
    user, passwd = opt("authentication", "username"), opt("authentication", "password")

    # command to be executed
    if args.folders:
       cmd = FOLDERLIST_CMD
    elif opt("archival", "archivedir"):
       cmd = ARCHIVE_CMD
    else:
       sys.exit("Either give the -f/--folders command, or specify the archive dir")

    # constraints
    includes, excludes = opt("archival", "includes"), opt("archival", "excludes")
    archivedir = opt("archival", "archivedir")
    loglevel = args.loglevel

    return (cmd, user, passwd, includes, excludes, archivedir, loglevel)


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

