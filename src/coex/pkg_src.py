from typing import List

from pathlib import Path
import subprocess
import logging
import platform

logger = logging.getLogger(__name__)


def pkg_src(sources: List[str], coex_path: Path) -> None:
    if not sources:
        logger.info("no sources")
        return

    (coex_path / "srcs").mkdir(parents=True)

    cmd = (
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
        + ["-f", str(coex_path / "srcs" / "src.tar.zst")]
        # include all specified sources
        + (["-c"] + list(sources))
    )
    logger.info("pkg_src %r", cmd)

    subprocess.check_call(cmd)
