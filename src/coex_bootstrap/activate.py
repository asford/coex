import logging
import os

logger = logging.getLogger(__name__)


def activate_env(prefix):
    # type: (str) -> None
    """Activate unpacked conda env at prefix.

    Updates os.environ for env activation.

    Args:
        prefix: Conda environment prefix.

    """
    logger.info("activate_env %s", locals())
    os.environ["PATH"] = ":".join([prefix + "/bin", os.environ.get("PATH", "")])
    os.environ["CONDA_PREFIX"] = prefix
