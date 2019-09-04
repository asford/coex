import textwrap
import pathlib
import subprocess
import json
import os

_test_versions = dict(python="3.6.3", numpy="1.16.3")
_test_env = textwrap.dedent(
    f"""
    dependencies:
        - python={_test_versions['python']}
        - numpy={_test_versions['numpy']}
        - nomkl
    """
)

_dump_version = textwrap.dedent(
    """
    from __future__ import print_function
    import numpy
    import json
    import sys

    print(
        json.dumps(
            dict(
                numpy=numpy.version.version,
                python=sys.version.split()[0],
            )
        )
    )
    """
)


def test_example_cli(tmp_path: pathlib.Path):
    tmp_path.cwd
    (tmp_path / "coex_environment.yml").open("w").write(_test_env)

    (tmp_path / "dump_version.py").open("w").write(_dump_version)

    subprocess.check_call(
        ["python"]
        + ["-m", "coex", "create"]
        + ["-f", "coex_environment.yml"]
        + ["--entrypoint", "python"]
        + ["-o", "python.coex"],
        cwd=tmp_path,
    )

    run_env = dict(os.environ)
    run_env["COEX_LOG_LEVEL"] = "DEBUG"

    # Direct execution as .coex dumps proper versions.
    result = subprocess.check_output(
        ["./python.coex", "dump_version.py"], cwd=tmp_path, env=run_env
    )

    assert json.loads(result) == _test_versions

    # Unzipped execution dumps proper versions as well.
    subprocess.check_output(
        ["unzip", "./python.coex", "-d", "python.coex.unzipped"],
        cwd=tmp_path,
        env=run_env,
    )

    unpacked_result = subprocess.check_output(
        ["python", "python.coex.unzipped", "dump_version.py"], cwd=tmp_path, env=run_env
    )

    assert json.loads(unpacked_result) == _test_versions


def test_example_archive(tmp_path: pathlib.Path):
    tmp_path.cwd
    (tmp_path / "coex_environment.yml").open("w").write(_test_env)

    script_path = tmp_path / "app/dump_version.py"
    script_path.parent.mkdir(parents=True)
    with script_path.open("w") as script:
        script.write("#!/usr/bin/env python")
        script.write(_dump_version)
    script_path.chmod(0o0755)

    subprocess.check_call(
        ["python"]
        + ["-m", "coex", "create"]
        + ["-f", "coex_environment.yml"]
        + ["--entrypoint", "app/dump_version.py"]
        + ["-o", "dump_version.coex"]
        + ["app"],
        cwd=tmp_path,
    )

    run_env = dict(os.environ)
    run_env["COEX_LOG_LEVEL"] = "INFO"

    # Direct execution as .coex dumps proper versions.
    result = subprocess.check_output(["./dump_version.coex"], cwd=tmp_path, env=run_env)

    assert json.loads(result) == _test_versions

    # Unzipped execution dumps proper versions as well.
    subprocess.check_output(
        ["unzip", "./dump_version.coex", "-d", "dump_version.coex.unzipped"],
        cwd=tmp_path,
        env=run_env,
    )

    unpacked_result = subprocess.check_output(
        ["python", "dump_version.coex.unzipped"], cwd=tmp_path, env=run_env
    )

    assert json.loads(unpacked_result) == _test_versions
