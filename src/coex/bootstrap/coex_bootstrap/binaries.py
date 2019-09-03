import os
import os.path
import pkgutil
import shutil
import stat
import logging

logger = logging.getLogger(__name__)

S_IXALL = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


class COEXBootstrapBinaries(object):
    required = ["zstd", "unzip"]

    def __init__(self, zstd, unzip):
        # type: (str) -> None
        self.zstd = zstd
        self.unzip = unzip

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

        binpaths = {b: os.path.join(prefix, "bin", b) for b in cls.required}

        for b, binpath in binpaths.items():
            logger.debug("unpack b=%r binpath=%r", b, binpath)
            with open(binpath, "wb") as of:
                of.write(pkgutil.get_data(package, os.path.join("bin", b)))
            os.chmod(binpath, os.stat(binpath).st_mode | S_IXALL)

        return cls(**binpaths)
