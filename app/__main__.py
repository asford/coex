from __future__ import print_function

import argparse
import fnmatch
import glob
import json
import logging
import os
import os.path
import pkgutil
import re
import pipes
import shutil
import stat
import subprocess
import sys
import zipfile
import zipimport
from distutils.util import strtobool

# Conda unpacking, cribbed from anaconda installer

on_win = bool(sys.platform == "win32")


def yield_lines(path):
    """Read non-comment lines at path."""
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        yield line


prefix_placeholder = (
    "/opt/anaconda1anaconda2"
    # this is intentionally split into parts,
    # such that running this program on itself
    # will leave it unchanged
    "anaconda3"
)


def read_has_prefix(path):
    """Return dict mapping filenames to tuples(placeholder, mode)"""

    import shlex

    res = {}
    try:
        for line in yield_lines(path):
            try:
                parts = [x.strip("\"'") for x in shlex.split(line, posix=False)]
                # assumption: placeholder and mode will never have a space
                placeholder, mode, f = parts[0], parts[1], " ".join(parts[2:])
                res[f] = (placeholder, mode)
            except (ValueError, IndexError):
                res[line] = (prefix_placeholder, "text")
    except IOError:
        pass
    return res


class PaddingError(Exception):
    pass


def binary_replace(data, a, b):
    """
    Perform a binary replacement of `data`, where the placeholder `a` is
    replaced with `b` and the remaining string is padded with null characters.
    All input arguments are expected to be bytes objects.
    """

    def replace(match):
        occurances = match.group().count(a)
        padding = (len(a) - len(b)) * occurances
        if padding < 0:
            raise PaddingError(a, b, padding)
        return match.group().replace(a, b) + b"\0" * padding

    pat = re.compile(re.escape(a) + b"([^\0]*?)\0")
    res = pat.sub(replace, data)
    assert len(res) == len(data)
    return res


def update_prefix(path, new_prefix, placeholder, mode):
    """Peform in-place prefix update on file."""
    logging.debug("update_prefix: %s", path)

    if on_win:
        # force all prefix replacements to forward slashes to simplify need
        # to escape backslashes - replace with unix-style path separators
        new_prefix = new_prefix.replace("\\", "/")

    path = os.path.realpath(path)
    with open(path, "rb") as fi:
        data = fi.read()
    if mode == "text":
        new_data = data.replace(placeholder.encode("utf-8"), new_prefix.encode("utf-8"))
    elif mode == "binary":
        if on_win:
            # anaconda-verify will not allow binary placeholder on Windows.
            # However, since some packages might be created wrong (and a
            # binary placeholder would break the package, we just skip here.
            return
        new_data = binary_replace(
            data, placeholder.encode("utf-8"), new_prefix.encode("utf-8")
        )
    else:
        sys.exit("Invalid mode:" % mode)

    if new_data == data:
        return
    st = os.lstat(path)
    # unlink in case the file is memory mapped
    os.unlink(path)
    with open(path, "wb") as fo:
        fo.write(new_data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def post_extract(prefix):
    """Update package files post-extract.

    Package has been extracted into env_path, leaving info/ and the package files.
    Update prefix files, run 'post-link', creates the conda metadata, and
    remove the info/ directory afterwards.
    """
    info_dir = os.path.join(prefix, "info")

    # with open(join(info_dir, 'index.json')) as fi:
    #     meta = json.load(fi)
    # dist = '%(name)s-%(version)s-%(build)s' % meta

    # TODO: Use paths.json, if available or fall back to this method
    has_prefix_files = read_has_prefix(os.path.join(info_dir, "has_prefix"))
    for f in sorted(has_prefix_files):
        placeholder, mode = has_prefix_files[f]
        try:
            update_prefix(os.path.join(prefix, f), prefix, placeholder, mode)
        except PaddingError:
            sys.exit("ERROR: placeholder '%s' too short in: %s\n" % (placeholder, f))

    repodata_record = os.path.join(info_dir, "repodata_record.json")
    if os.path.exists(repodata_record):
        repodata = json.load(open(repodata_record, "rb"))
        if repodata.get("noarch", None) == "python":
            logging.info("unpacking noarch")
            target = glob.glob(os.path.join(prefix, "lib/python*/site-packages"))[0]
            for f in glob.glob(os.path.join(prefix, "site-packages/*")):
                shutil.move(f, target)

    post_link = os.path.join(prefix, "info/recipe/post-link.sh")
    if os.path.exists(post_link):
        # TODO: Enable post-link behaviors?
        logging.warning("skiping post-link script %s", post_link)
        # env = os.environ
        # env['PREFIX'] = prefix
        # subprocess.check_call(post_link, env=env, shell=True)

    shutil.rmtree(info_dir)


class ZipPkgs:
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


class FilePkgs:
    def __init__(self, target):
        self._path = target
        self.pkgs = ["pkgs/" + n for n in os.listdir(os.path.join(target, "pkgs"))]

    def open(self, name):
        return open(self._path + "/" + name, "rb")

    def extract_cmd(self, name):
        return "cat %s" % (pipes.quote(os.path.join(self._path, name)))


def get_pkgs():
    loader = pkgutil.get_loader(__name__)
    if isinstance(loader, zipimport.zipimporter):
        return ZipPkgs(loader.archive)
    else:
        return FilePkgs(os.path.dirname(__file__))


class COEXOptions(object):
    work_dir = "/tmp"
    cleanup = True
    verbose = False
    program_args = []

    def __init__(self, args=None):
        if args is None:
            args = sys.argv[1:]

        parser = argparse.ArgumentParser(
            ".cex trampoline",
            usage="Control variables for the conda executable packages",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument(
            "--work_dir",
            type=str,
            help="Work directory to cex unpack and run. Override: COEX_WORK_DIR",
            default=os.environ.get("COEX_WORK_DIR", self.work_dir),
        )
        parser.add_argument(
            "--cleanup",
            type=bool,
            help="Remove environment after run. Override: COEX_CLEANUP",
            default=os.environ.get("COEX_CLEANUP", self.cleanup),
        )
        parser.add_argument(
            "--verbose",
            type=bool,
            help="Print COEX status to stderr. Override: COEX_VERBOSE",
            default=os.environ.get("COEX_VERBOSE", self.verbose),
        )

        if strtobool(os.environ.get("COEX_ARGS", "false")):
            if "--" in args:
                split_idx = args.index("--")
                cex_args = args[:split_idx]
                program_args = args[split_idx:][1:]
            else:
                cex_args = args
                program_args = []
        else:
            cex_args = []
            program_args = args

        parsed = parser.parse_args(cex_args)
        for k, v in parsed.__dict__.items():
            setattr(self, k, v)
        self.program_args = program_args

    def __repr__(self):
        return "COEXOptions(%s)" % self.__dict__


def main(options):
    # type: (COEXOptions) -> None
    if options.verbose:
        logging.basicConfig(level=logging.INFO)

    logging.info("options=%s", options)

    run_dir = os.path.join(
        options.work_dir, "%s_%i" % (os.path.basename(__file__), os.getpid())
    )
    logging.info("run_dir=%s", run_dir)
    os.makedirs(run_dir)

    conda_dir = os.path.join(run_dir, "conda")
    logging.info("run_dir=%s", run_dir)
    os.makedirs(conda_dir)

    pkgs = get_pkgs()
    logging.info("pkgs.pkgs=%s", pkgs.pkgs)

    # Horrid hack, unpack python first so we can noarch packages
    for p in sorted(pkgs.pkgs, key=lambda v: 0 if v.startswith("pkgs/python-") else 1):
        extract = "%s | zstd -d | tar -xC %s" % (
            pkgs.extract_cmd(p),
            pipes.quote(conda_dir),
        )

        logging.info("extracting pkg=%s cmd=%s", p, extract)
        subprocess.check_call(extract, shell=True)

        logging.info("post_extract pkg=%s prefix=%s", p, conda_dir)
        post_extract(conda_dir)


if __name__ == "__main__":
    options = COEXOptions()
    main(options)
