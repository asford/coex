import json
import os.path
import pkgutil


class COEXBootstrapConfig(object):
    """Coex package bootstrap configuration, packed under 'coex_bootstrap.json'."""

    def __init__(self, entrypoint):
        # type: (str) -> None
        """Init bootstrap config.

        Args:
            entrypoint: coex executable entrypoint.

        """
        self.entrypoint = entrypoint

    def __repr__(self):  # noqa: D
        # type: () -> str
        return "COEXBootstrapConfig(entrypoint={self.entrypoint!r}".format(self=self)

    def as_dict(self):
        # type: () -> dict
        """As json-compatible object."""
        return {"entrypoint": self.entrypoint}

    @classmethod
    def from_dict(cls, obj):
        # type: (dict) -> COEXBootstrapConfig
        """From json-compatible object."""
        return cls(**obj)

    def write_to(self, prefix):
        # type: (str) -> None
        """Write to coex package bootstrap.json.

        Args:
            prefix: Coex package build root.

        """

        with open(os.path.join(prefix, "coex_bootstrap.json"), "w") as config_out:
            json.dump(self.as_dict(), config_out, indent=2)

    @classmethod
    def read_from(cls, prefix=None, package=None):
        # type: (str, str) -> COEXBootstrapConfig
        """Read coex package bootstrap.json.

        Reads from zipped coex package OR unpacked coex prefix.

        Args:
            prefix: Unpacked coex package prefix.
            package: Zipped coex package name.

        Returns:
            Parsed bootstrap.json

        Raises:
            ValueError: Invalid prefix/package.

        """
        if prefix and not package:
            config = open(os.path.join(prefix, "coex_bootstrap.json"), "rb").read()
        elif package and not prefix:
            config_data = pkgutil.get_data(package, "coex_bootstrap.json")

            if config_data is None:
                raise ValueError(
                    "package did not include coex_bootstrap.json: %s",
                    dict(package=package),
                )
            else:
                config = config_data

        else:
            raise ValueError(
                "One of prefix or package must be provided: %s",
                dict(prefix=prefix, package=package),
            )

        return cls.from_dict(json.loads(config.decode("utf-8")))
