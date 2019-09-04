# (c) 2012-2016 Anaconda, Inc. / https://anaconda.com
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# http://opensource.org/licenses/BSD-3-Clause
#
# Extensions (c) 2019 coex authors
"""Conda package install, cribbed from miniconda installer."""

try:
    import typing
except ImportError:
    pass
import glob
import json
import logging
import os
import re
import shlex
import shutil
import stat
import sys

logger = logging.getLogger(__name__)

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
    # type: (str) -> typing.Dict[str, typing.Tuple[str, str]]
    """Read info/has_prefix file.

    Args:
        path: has_prefix file path.

    Returns:
        Mapping of {filename : (placeholder, mode)}

    """

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
    """Binary prefix replacement failed, insufficient padding available."""

    pass


def binary_replace(data, a, b):
    # type: (bytes, bytes, bytes) -> bytes
    """Perform binary prefix replacement.

    Perform a binary replacement of `data`, where the placeholder `a` is
    replaced with `b` and the remaining string is padded with null characters.
    All input arguments are expected to be bytes objects.

    Raises:
        PaddingError: Insufficient padding available for replacement.

    Returns: prefix-replaced data

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
    # type: (str) -> None
    """Update package files post-extract.

    Package has been extracted into `prefix`, leaving `info/` and the package files.
    Update prefix files, detect 'post-link', and remove `info/` directory.

    Args:
        prefix: Conda env prefix post package extraction.

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
        repodata = json.loads(open(repodata_record, "rb").read().decode("utf-8"))
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
