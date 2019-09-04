import logging
import os.path
import platform
import shutil
import subprocess
from itertools import chain
from pathlib import Path
from typing import Set

from conda._vendor.boltons.setutils import IndexedSet
from conda.base.context import context
from conda.core.link import UnlinkLinkTransaction
from conda.core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
from conda.core.solve import Solver
from conda.models.channel import Channel, prioritize_channels
from conda.models.records import PackageCacheRecord, PackageRecord
from conda_env.specs.yaml_file import YamlFileSpec

logger = logging.getLogger(__name__)


def pkg_env(environment_file: Path, coex_path: Path, cache_dir: Path) -> None:

    # Resolve environment file to dependencies
    # Logic culled from conda-env
    spec = YamlFileSpec(filename=str(environment_file))
    env = spec.environment

    logging.info(env.dependencies)

    assert set(env.dependencies) == {
        "conda"
    }, f"coex environments do not support pip dependencies: {env}"

    channel_urls = [chan for chan in env.channels if chan != "nodefaults"]
    if "nodefaults" not in env.channels:
        channel_urls.extend(context.channels)
    _channel_priority_map = prioritize_channels(channel_urls)

    # Setup an dummpy environment resolution for install into /dev/null
    # Execute fetch-and-extract operations for required conda packages
    prefix = "/dev/null"

    channels = IndexedSet(Channel(url) for url in _channel_priority_map)
    subdirs = IndexedSet(os.path.basename(url) for url in _channel_priority_map)

    solver = Solver(prefix, channels, subdirs, specs_to_add=env.dependencies["conda"])
    transaction: UnlinkLinkTransaction = solver.solve_for_transaction()

    logging.info(transaction)

    transaction.download_and_extract()

    # Resolve all the, now extracted, target packages in the filesystem
    fetcher: ProgressiveFetchExtract = transaction._pfe

    target_records: Set[PackageRecord] = set(fetcher.link_precs)
    logging.debug("target_records=%s", target_records)

    extracted: Set[PackageCacheRecord] = {
        next(
            (
                pcrec
                for pcrec in chain(
                    *(
                        PackageCacheData(pkgs_dir).query(precord)
                        for pkgs_dir in context.pkgs_dirs
                    )
                )
                if pcrec.is_extracted
            ),
            None,
        )
        for precord in target_records
    }

    logging.debug("extracted=%s", extracted)

    # Repackage into a single-file .zst in the cache, then copy into the output
    # package.
    output_path = coex_path / "pkgs"
    for e in extracted:
        extracted_dir = Path(e.extracted_package_dir)
        pkgname = extracted_dir.name + ".tar.zst"

        cache_dir.mkdir(parents=True, exist_ok=True)

        if not (cache_dir / pkgname).exists():
            pkg_cmd = (
                # tar filtered through zstd
                # Seeing errors on macos 10.13 image when using --use-compress-program
                # with arguments, consider (a) installing conda-forge tar or (b) using
                # a wrapper script if zstd arguments are needed
                [
                    "tar",
                    "--use-compress-program",
                    "zstd -T0" if platform.system() != "Darwin" else "zstd",
                ]
                # write to archive file
                + ["-f", str(cache_dir / pkgname)]
                # chdir to extracted package directory
                + ["-C", str(extracted_dir)]
                # and add all package dirs
                + (["-c"] + [f.name for f in extracted_dir.iterdir()])
            )
            logging.info("packaging: %s", pkg_cmd)
            subprocess.check_call(pkg_cmd)

        output_path.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cache_dir / pkgname, output_path / pkgname)

    return extracted
