import json
import os.path
import pkgutil


class COEXBootstrapConfig(object):
    def __init__(self, entrypoint):
        # type: (str) -> None
        self.entrypoint = entrypoint

    def __repr__(self):
        # type: () -> str
        return "COEXBootstrapConfig(entrypoint={self.entrypoint!r}".format(self=self)

    def as_dict(self):
        # type: () -> dict
        return {"entrypoint": self.entrypoint}

    @classmethod
    def from_dict(cls, obj):
        # type: (dict) -> COEXBootstrapConfig
        return cls(**obj)

    def write_to(self, prefix):
        # type: (str) -> None
        with open(os.path.join(prefix, "coex_bootstrap.json"), "w") as config_out:
            json.dump(self.as_dict(), config_out, indent=2)

    @classmethod
    def read_from(cls, prefix=None, package=None):
        # type: (str, str) -> COEXBootstrapConfig
        if prefix and not package:
            config = open(os.path.join(prefix, "coex_bootstrap.json"), "r").read()
        elif package and not prefix:
            config = pkgutil.get_data(package, "coex_bootstrap.json")
        else:
            raise ValueError(
                "One of prefix or package must be provided: %s",
                dict(prefix=prefix, package=package),
            )

        return cls.from_dict(json.loads(config))
