import fnmatch
import glob
import logging
import os
import os.path
import subprocess
import zipfile

logger = logging.getLogger(__name__)


class ZipPkgs(object):
    def __init__(self, target, fnmatch_pattern):
        logger.debug("ZipPkgs target=%s fnmatch_pattern=%s")
        self._zipfile = zipfile.ZipFile(target)
        self.names = fnmatch.filter(self._zipfile.namelist(), fnmatch_pattern)

    def open(self, name):
        return self._zipfile.open(name)

    def extract_cmd(self, coex_binaries, name):
        return [coex_binaries.unzip, "-p", self._zipfile.filename, name]

    def pkgs(self, coex_binaries):
        return [PkgHandle(p, self.extract_cmd(coex_binaries, p)) for p in self.names]


class FilePkgs(object):
    def __init__(self, target, glob_pattern):
        _full_glob = os.path.join(target, glob_pattern)
        logger.debug("FilePkgs target=%s glob_pattern=%s _full_glob=%s")
        self._path = target
        self.names = [os.path.relpath(p, target) for p in glob.glob(_full_glob)]

    def extract_cmd(self, coex_binaries, name):
        return ["cat", os.path.join(self._path, name)]

    def pkgs(self, coex_binaries):
        return [PkgHandle(p, self.extract_cmd(coex_binaries, p)) for p in self.names]


class PkgHandle(object):
    def __init__(self, name, extract_cmd):
        # type: (str, str) -> None
        self.name = name
        self.extract_cmd = extract_cmd

    def extract(self, coex_binaries, prefix_dir):

        untar_cmd = (
            ["tar"]
            + ["--use-compress-program", coex_binaries.zstd]
            + ["-x", "-C", prefix_dir]
        )

        logging.debug(
            "extract pkg=%s extract=%r untar=%r", self.name, self.extract_cmd, untar_cmd
        )

        extract = subprocess.Popen(self.extract_cmd, stdout=subprocess.PIPE, bufsize=-1)
        untar = subprocess.Popen(untar_cmd, stdin=extract.stdout, bufsize=-1)

        extract.wait()
        if extract.returncode:
            raise subprocess.CalledProcessError(extract.returncode, extract.args)

        untar.wait()
        if untar.returncode:
            raise subprocess.CalledProcessError(extract.returncode, extract.args)
