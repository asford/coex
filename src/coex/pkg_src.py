from typing import List

from pathlib import Path
import subprocess
import logging

logger = logging.getLogger(__name__)


def pkg_src(sources: List[str], coex_path: Path) -> None:
    if not sources:
        logger.info("no sources")
        return

    (coex_path / "srcs").mkdir(parents=True)

    cmd = (
        # tar filtered through multithreaded zstd
        ["tar", "--use-compress-program", "zstd -T0"]
        # write to archive file
        + ["-f", str(coex_path / "srcs" / "src.tar.zst")]
        # include all specified sources
        + (["-c"] + list(sources))
    )
    logger.info("pkg_src %r", cmd)

    subprocess.check_call(cmd)
