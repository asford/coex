import os
import os.path
import pkgutil
import shutil
import stat
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

S_IXALL = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

# Backported which from python 3
def which(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.

    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.

    """
    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(fn, mode):
        return os.path.exists(fn) and os.access(fn, mode) and not os.path.isdir(fn)

    # If we're given a path with a directory part, look it up directly rather
    # than referring to PATH directories. This includes checking relative to the
    # current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd
        return None

    if path is None:
        path = os.environ.get("PATH", os.defpath)
    if not path:
        return None
    path = path.split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        # If it does match, only test that one, otherwise we have to try
        # others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if _access_check(name, mode):
                    return name
    return None


class COEXBootstrapBinaries(object):
    required = ["zstd", "unzip", "tar"]

    def __init__(self, zstd, unzip, tar):
        # type: (str, str, str) -> None
        self.zstd = zstd
        self.unzip = unzip
        self.tar = tar

    def __repr__(self):
        # type: () -> str
        return (
            "COEXBootstrapBinaries("
            "zstd={self.zstd!r}, "
            "unzip={self.unzip!r}, "
            "tar={self.tar!r}"
            ")".format(self=self)
        )

    @classmethod
    def copy_to(cls, prefix):
        # type: (str) -> None
        logger.debug("copy_to prefix=%r", prefix)
        bindir = os.path.join(prefix, "bin")
        if not os.path.exists(bindir):
            os.makedirs(bindir)

        for b in cls.required:
            shutil.copy(shutil.which(b), bindir)

    @classmethod
    def unpack(cls, prefix=None, package=None):
        # type: (str, str) -> COEXBootstrapBinaries
        logger.info("unpack prefix=%r package=%r", prefix, package)
        bindir = os.path.join(prefix, "bin")
        if not os.path.exists(bindir):
            os.makedirs(bindir)

        binpaths = {}

        for b in cls.required:
            pkg_bin = pkgutil.get_data(package, os.path.join("bin", b))

            if pkg_bin:
                binpath = os.path.join(prefix, "bin", b)
                logger.debug("unpack b=%r binpath=%r", b, binpath)
                with open(binpath, "wb") as of:
                    of.write(pkg_bin)
                os.chmod(binpath, os.stat(binpath).st_mode | S_IXALL)
                binpaths[b] = binpath
            else:
                logger.debug("system b=%r", which(b))
                binpaths[b] = b

        return cls(**binpaths)
