import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
        return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
        name = "pygmailarchive",
        version = "0.3.7-koodaamo",
        author = "Andreas Pakulat, Petri Savolainen",
        author_email = "apaku@gmx.de, petri.savolainen@iki.fi",
        description = ("An utility to archive Mails from GMail accounts."),
        license = "BSD",
        keywords = "gmail imap archive",
        url = "https://github.com/koodaamo/pygmailarchive",
        install_requires = ["IMAPClient"],
        scripts = ["gmailarchive.py"],
        packages=find_packages(exclude=['ez_setup']),
        data_files = [('share/doc/pygmailarchive', ['README','LICENSE'])],
        long_description = read('README'),
        classifiers = [
            "Development Status :: 3 - Alpha",
            "Topic :: Utilities",
            "Environment :: Console",
            "License :: OSI Approved :: BSD License",
        ],
)
