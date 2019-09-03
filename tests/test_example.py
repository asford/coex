import textwrap
import pathlib
import subprocess
import json
import os


def test_example(tmp_path: pathlib.Path):
    tmp_path.cwd
    (tmp_path / "coex_environment.yml").open("w").write(
        textwrap.dedent(
            """
            dependencies:
                - python=3.6.3
                - numpy=1.16.3
                - nomkl
            """
        )
    )

    (tmp_path / "dump_version.py").open("w").write(
        textwrap.dedent(
            """
            from __future__ import print_function
            import numpy
            import json
            import sys

            print(
                json.dumps(
                    dict(
                        numpy=numpy.version.version,
                        sys=sys.version.split()[0],
                    )
                )
            )
            """
        )
    )

    subprocess.check_call(
        "python"
        " -m coex create"
        " -f coex_environment.yml"
        " --entrypoint python"
        " -o python.coex",
        shell=True,
        cwd=tmp_path,
    )

    run_env = dict(os.environ)
    run_env["COEX_LOG_LEVEL"] = "INFO"

    result = subprocess.check_output(
        "./python.coex dump_version.py", shell=True, cwd=tmp_path, env=run_env
    )

    assert json.loads(result) == dict(numpy="1.16.3", sys="3.6.3")
