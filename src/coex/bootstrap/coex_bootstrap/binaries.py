import os
import os.path
import pkgutil
import shutil
import stat
import logging

logger = logging.getLogger(__name__)

S_IXALL = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


class COEXBootstrapBinaries(object):
    required = ["zstd", "unzip", "tar"]

    def __init__(self, zstd, unzip, tar):
        # type: (str) -> None
        self.zstd = zstd
        self.unzip = unzip
        self.tar = tar

    def __repr__(self):
        # type: () -> str
        return "COEXBootstrapBinaries(zstd={self.zstd!r}, unzip={self.unzip!r})".format(
            self=self
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
        logger.info("unpack prefix=%r package=%r", prefix, package)
        # type: (str, str) -> COEXBootstrapBinaries
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
                logger.debug("system b=%r", b)
                binpaths[b] = b

        return cls(**binpaths)
