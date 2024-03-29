from __future__ import print_function

import argparse
import logging
import os
import os.path
import pkgutil
import shutil
import subprocess
import sys
import time
import zipimport
from collections import defaultdict
from distutils.util import strtobool

from coex_bootstrap.activate import activate_env
from coex_bootstrap.binaries import COEXBootstrapBinaries
from coex_bootstrap.config import COEXBootstrapConfig
from coex_bootstrap.install import post_extract
from coex_bootstrap.unpack import file_pkgs, zip_pkgs

try:
    import typing
except ImportError:
    pass


class SectionTimer(object):
    """Accumulate timers into sections."""

    sections = defaultdict(float)  # type: typing.Dict[str, float]

    def __init__(self, name):
        # type: (str) -> None
        """Start timer adding to given section name."""
        self.name = name
        self.start = 0.0
        self.span = 0.0

    def __enter__(self):  # noqa: D
        # type: () -> SectionTimer
        self.start = time.time()
        return self

    def __exit__(self, *args):  # noqa: D
        # type: (*typing.Any) -> None
        self.span = time.time() - self.start
        self.sections[self.name] += self.span


class COEXOptions(object):
    """Run-time coex options."""

    work_dir = "/tmp"
    cleanup = True
    log_level = None
    program_args = []  # type: typing.List[str]

    def __init__(self, args=None):
        # type: (typing.Optional[typing.List[str]]) -> None
        """Load options from env and/or command line args.

        Args:
            args: Program arguments, loads sys.argv if None.
        """
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
            "--log-level",
            dest="log_level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Log COEX status to stderr. Override: COEX_LOG_LEVEL",
            default=os.environ.get("COEX_LOG_LEVEL", self.log_level),
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

    def __repr__(self):  # noqa: D
        return "COEXOptions(%s)" % self.__dict__


def resolve_entrypoint(entrypoint, prefix_dir):
    # type: (str, str) -> str
    """Resolve coex entrypoint into a executable path.

    Coex entrypoint is either (a) an executable name, resolved in the coex
    execution environment or (b) a path to an executable, absolute or relative
    to the usr data prefix.

    Args:
        entrypoint: coex entrypoint
        prefix_dir: usr prefix path

    Returns:
        Executable value, expanded to abs path.

    """
    entrypoint = os.path.expandvars(entrypoint)

    if not os.path.dirname(entrypoint):
        # entrypoint is a bare executable name, exec as is
        return entrypoint
    elif os.path.isabs(entrypoint):
        # entrypoint is an absolute path, exec as is
        return entrypoint
    else:
        # entrypoint is a relative path, evaluate wrt the prefix
        return os.path.join(prefix_dir, entrypoint)


def main(__name__, __file__, options):
    # type: (str, str, COEXOptions) -> None
    """Main bootstrap entrypoint.

    Main bootstrap, unpacks coex and executes entrypoint program.

    Args:
        __name__: __name__ of main module.
        __file__: __file__ of main module.
        options: Initialized COEXOptions.

    """
    with SectionTimer("total"):
        if options.log_level:
            logging.basicConfig(level=logging.getLevelName(options.log_level))

        logging.info("options=%s", options)

        config = COEXBootstrapConfig.read_from(package=__name__)
        logging.info("config=%s", config)

        run_dir = os.path.join(
            options.work_dir, "%s_%i" % (os.path.basename(__file__), os.getpid())
        )
        logging.info("run_dir=%s", run_dir)
        os.makedirs(run_dir)

        conda_dir = os.path.join(run_dir, "conda")
        logging.info("run_dir=%s", run_dir)
        os.makedirs(conda_dir)

        with SectionTimer("get_binaries"):
            coex_binaries = COEXBootstrapBinaries.unpack(run_dir, __name__)
            logging.debug("coex_binaries %s", coex_binaries)

        ### Unpack and install conda packages
        with SectionTimer("get_pkgs"):
            loader = pkgutil.get_loader(__name__)
            if isinstance(loader, zipimport.zipimporter):
                pkgs = zip_pkgs(loader.archive, "pkgs/?*")
            else:
                pkgs = file_pkgs(os.path.dirname(__file__), "pkgs/*")
        logging.debug("pkgs=%s", pkgs)

        # Horrid hack, unpack python first so we can noarch packages
        for p in sorted(
            pkgs, key=lambda v: 0 if v.name.startswith("pkgs/python-") else 1
        ):
            with SectionTimer("extract"):
                p.extract(coex_binaries, conda_dir)

            with SectionTimer("post_extract"):
                logging.debug("post_extract pkg=%s prefix=%s", p, conda_dir)
                post_extract(conda_dir)

        ### Unpack usr packages
        usr_dir = os.path.join(run_dir, "usr")
        logging.info("run_dir=%s", run_dir)
        os.makedirs(usr_dir)

        with SectionTimer("get_srcs"):
            loader = pkgutil.get_loader(__name__)
            if isinstance(loader, zipimport.zipimporter):
                srcs = zip_pkgs(loader.archive, "srcs/?*")
            else:
                srcs = file_pkgs(os.path.dirname(__file__), "srcs/*")
        logging.debug("srcs=%r", srcs)

        for p in srcs:
            with SectionTimer("extract"):
                p.extract(coex_binaries, usr_dir)

        ### Activate the target environment
        with SectionTimer("activate"):
            activate_env(conda_dir)
            os.environ["COEX_USR_PREFIX"] = usr_dir
            os.environ["COEX_ROOT_PREFIX"] = run_dir

    logging.info("setup_times %r", dict(SectionTimer.sections))
    SectionTimer.sections.clear()

    cmd = [
        resolve_entrypoint(config.entrypoint, os.path.join(run_dir, "usr"))
    ] + options.program_args
    logging.info("call %s", cmd)
    try:
        subprocess.call(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        if options.cleanup:
            with SectionTimer("cleanup"):
                logging.info("cleanup run_dir=%s", run_dir)
                shutil.rmtree(run_dir)

        logging.info("cleanup_times %r", dict(SectionTimer.sections))
        SectionTimer.sections.clear()
