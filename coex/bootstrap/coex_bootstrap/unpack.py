import fnmatch
import logging
import os
import os.path
import pipes
import pkgutil
import subprocess
import zipfile
import zipimport

logger = logging.getLogger(__name__)


class ZipPkgs(object):
    def __init__(self, target):
        self._zipfile = zipfile.ZipFile(target)
        self.pkgs = fnmatch.filter(self._zipfile.namelist(), "pkgs/?*")

    def open(self, name):
        return self._zipfile.open(name)

    def extract_cmd(self, name):
        return "unzip -p %s %s" % (
            pipes.quote(self._zipfile.filename),
            pipes.quote(name),
        )


class FilePkgs(object):
    def __init__(self, target):
        self._path = target
        self.pkgs = ["pkgs/" + n for n in os.listdir(os.path.join(target, "pkgs"))]

    def open(self, name):
        return open(self._path + "/" + name, "rb")

    def extract_cmd(self, name):
        return "cat %s" % (pipes.quote(os.path.join(self._path, name)))


class PkgHandle(object):
    def __init__(self, name, extract_cmd):
        # type: (str, str) -> None
        self.name = name
        self.extract_cmd = extract_cmd

    def extract(self, prefix_dir):

        extract = "%s | zstd -d | tar -xC %s" % (
            self.extract_cmd,
            pipes.quote(prefix_dir),
        )

        logging.debug("extract pkg=%s cmd=%s", self.name, extract)
        subprocess.check_call(extract, shell=True)


def get_pkgs():
    """Get pkgs handles for current archive."""
    # type: () -> list

    loader = pkgutil.get_loader(__name__)
    if isinstance(loader, zipimport.zipimporter):
        pkg_src = ZipPkgs(loader.archive)
    else:
        pkg_src = FilePkgs(os.path.dirname(__file__))

    return [PkgHandle(p, pkg_src.extract_cmd(p)) for p in pkg_src.pkgs]
