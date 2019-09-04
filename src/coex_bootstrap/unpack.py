import fnmatch
import glob
import logging
import os
import os.path
import subprocess
import zipfile

logger = logging.getLogger(__name__)


def zip_pkgs(target, fnmatch_pattern):
    logger.debug("zip_pkgs target=%s fnmatch_pattern=%s")
    _zipfile = zipfile.ZipFile(target)
    return [
        ZipPkgHandle(target, name)
        for name in fnmatch.filter(_zipfile.namelist(), fnmatch_pattern)
    ]


class ZipPkgHandle(object):
    def __init__(self, target, name):
        # type: (str, str) -> None
        self.target = target
        self.name = name

    def __repr__(self):
        return "ZipPkgHandle(target={self.target!r}, name={self.name!r})".format(
            self=self
        )

    def extract(self, coex_binaries, prefix_dir):

        extract_cmd = [coex_binaries.unzip, "-p", self.target, self.name]

        untar_cmd = (
            [coex_binaries.tar]
            # tar filtered through zstd
            # Seeing errors on macos 10.13 image when using --use-compress-program
            # with arguments, consider using a wrapper script if zstd arguments
            # are needed.
            + ["--use-compress-program", coex_binaries.zstd]
            + ["-x", "-C", prefix_dir]
        )

        logging.debug(
            "extract pkg=%s extract=%r untar=%r", self.name, extract_cmd, untar_cmd
        )

        extract = subprocess.Popen(extract_cmd, stdout=subprocess.PIPE, bufsize=-1)
        untar = subprocess.Popen(untar_cmd, stdin=extract.stdout, bufsize=-1)

        extract.wait()
        if extract.returncode:
            raise subprocess.CalledProcessError(extract.returncode, extract_cmd)

        untar.wait()
        if untar.returncode:
            raise subprocess.CalledProcessError(untar.returncode, untar_cmd)


def file_pkgs(target, glob_pattern):
    _full_glob = os.path.join(target, glob_pattern)
    logger.debug("file_pkgs target=%s glob_pattern=%s _full_glob=%s")

    names = [os.path.relpath(p, target) for p in glob.glob(_full_glob)]

    return [FilePkgHandle(target, name) for name in names]


class FilePkgHandle(object):
    def __init__(self, target, name):
        # type: (str, str) -> None
        self.target = target
        self.name = name

    def __repr__(self):
        return "FilePkgHandle(target={self.target!r}, name={self.name!r})".format(
            self=self
        )

    def extract(self, coex_binaries, prefix_dir):
        untar_cmd = (
            [coex_binaries.tar]
            # tar filtered through zstd
            # Seeing errors on macos 10.13 image when using --use-compress-program
            # with arguments, consider using a wrapper script if zstd arguments
            # are needed.
            + ["--use-compress-program", coex_binaries.zstd]
            + ["-x", "-C", prefix_dir]
        )

        logging.debug("extract pkg=%s untar=%r", self.name, untar_cmd)

        with open(os.path.join(self.target, self.name), "rb") as inf:
            untar = subprocess.Popen(untar_cmd, stdin=inf, bufsize=-1)
            untar.wait()
            if untar.returncode:
                raise subprocess.CalledProcessError(untar.returncode, untar_cmd)
