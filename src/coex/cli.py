import contextlib
import json
import logging
import shutil
import tempfile
import zipapp
from pathlib import Path

import attr
import click

import coex_bootstrap
from coex_bootstrap.binaries import COEXBootstrapBinaries
from coex_bootstrap.config import COEXBootstrapConfig
from coex.pkg_env import pkg_env
from coex.pkg_src import pkg_src

logger = logging.getLogger(__name__)


@attr.s()
class COEXConfig:
    cleanup: bool = attr.ib()
    cache: Path = attr.ib(converter=Path)


pass_config = click.make_pass_decorator(COEXConfig, ensure=True)


@click.group()
@click.option(
    "--cache", type=click.Path(file_okay=False, writable=True), default="coex_cache"
)
@click.option("--cleanup/--no-cleanup", default=True)
@click.pass_context
def cli(ctx, **kwargs):
    logging.basicConfig(level=logging.INFO)
    logging.info("cli %s", kwargs)
    ctx.obj = COEXConfig(**kwargs)


@cli.command()
@pass_config
@click.option(
    "--file",
    "-f",
    "env_file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
@click.option("--entrypoint", type=str, required=True)
@click.option("--output", "-o", type=click.Path(), required=True)
@click.argument("sources", type=click.Path(exists=True), nargs=-1)
def create(config: COEXConfig, env_file, entrypoint, output, sources):
    logger.info("create %s", locals())
    env_file = Path(env_file)

    with contextlib.ExitStack() as cstack:

        # Create the working directory
        config.cache.mkdir(parents=True, exist_ok=True)
        build_dir = Path(tempfile.mkdtemp(prefix="build_", dir=str(config.cache)))

        if config.cleanup:
            cstack.callback(shutil.rmtree, build_dir)

        logging.info("start build build_dir=%s", build_dir)
        build_root = build_dir / "root"

        # Copy coex_bootstrap template into coex src
        coex_bootstrap_path = Path(coex_bootstrap.__file__).parent
        logging.info("setup coex_bootstrap_path=%s", coex_bootstrap_path)
        shutil.copytree(
            str(coex_bootstrap_path),
            str(build_root / "coex_bootstrap"),
            ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "__main__.py"),
        )
        shutil.copy(
            str(coex_bootstrap_path / "__main__.py"), str(build_root / "__main__.py")
        )

        # Copy zstd binary into bootstrap bin
        COEXBootstrapBinaries.copy_to(build_root)

        # Write a bootstrap configuration object into
        bootstrap_config = COEXBootstrapConfig(entrypoint=entrypoint)

        with open(build_root / "coex_bootstrap.json", "w") as config_out:
            json.dump(bootstrap_config.as_dict(), config_out, indent=2)

        # Copy env pkgs into coex src
        pkg_env(env_file, build_root, config.cache / "pkgs")

        # Copy src files into coex src
        pkg_src(sources, build_root)

        # Create zipapp archive
        logging.info("create_archive source=%s target=%s", build_root, output)
        zipapp.create_archive(build_root, output, interpreter="/usr/bin/env python")
