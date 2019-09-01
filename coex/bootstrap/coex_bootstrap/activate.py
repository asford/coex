import logging
import os

logger = logging.getLogger(__name__)


def activate_env(prefix):
    # type: (str) -> None
    logger.info("activate_env %s", locals())
    os.environ["PATH"] = ":".join([prefix + "/bin", os.environ.get("PATH", "")])
    os.environ["CONDA_PREFIX"] = prefix
