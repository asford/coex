try:
    import typing
except ImportError:
    pass

import logging
import os
import os.path
import pkgutil
import shutil
import stat
import sys

logger = logging.getLogger(__name__)

S_IXALL = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


def which(cmd, mode=os.F_OK | os.X_OK, path=None):
    # type: (str, int, typing.Optional[str]) -> typing.Optional[str] # noqa: I
    """Find path of cmd, or None if not found.

    Backported python3 shutil.which. Given a command, mode, and a PATH string,
    return the path which conforms to the given mode on the PATH, or None if
    there is no such file.

    Args:
        cmd: Command name.
        mode: Check for given mode, defaults to os.F_OK | os.X_OK.
        path: Check given search path, defaults to os.environ.get("PATH")

    Returns: Resolved cmd path, or None

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

    paths = path.split(os.pathsep)  # type: typing.List[str]

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            paths.insert(0, os.curdir)

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

    seen = set()  # type: typing.Set[str]
    for dir in paths:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if _access_check(name, mode):
                    return name
    return None


class COEXBootstrapBinaries(object):
    """Set of binaries required for COEX bootstrap."""

    required = ["zstd", "unzip", "tar"]

    def __init__(self, zstd, unzip, tar):
        # type: (str, str, str) -> None
        """Init with executable paths."""
        self.zstd = zstd
        self.unzip = unzip
        self.tar = tar

    def __repr__(self):  # noqa: D
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
        """Pack binaries from current environment into coex prefix."""

        logger.debug("copy_to prefix=%r", prefix)
        bindir = os.path.join(prefix, "bin")
        if not os.path.exists(bindir):
            os.makedirs(bindir)

        for b in cls.required:
            bin_path = shutil.which(b)
            if bin_path is None:
                raise ValueError("Unable to resolve binary: %s" % b)
            shutil.copy(bin_path, bindir)

    @classmethod
    def unpack(cls, prefix, package):
        # type: (str, str) -> COEXBootstrapBinaries
        """Unpack binaries from coex into run prefix.

        Args:
            prefix: coex run prefix
            package: coex package, zipped or unpacked.

        Returns:
            Path of unpacked binaries in prefix.

        """

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
