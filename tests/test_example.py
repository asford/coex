import json
import pathlib
import subprocess
import textwrap
import typing

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

_bootstrap_run_envs: typing.Dict[str, typing.List[str]] = {
    "system": [],
    "py27": ["python=2.7"],
    "py35": ["python=3.5"],
    "py36": ["python=3.6"],
}


def test_example_cli(tmp_path: pathlib.Path):
    """Verify README.MD example via cli."""
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

    # Unzip for filesystem execution
    subprocess.check_output(
        ["unzip", "./python.coex", "-d", "python.coex.unzipped"], cwd=tmp_path
    )

    for sname, deps in _bootstrap_run_envs.items():
        # Execute in clean running environment
        run_env = {}
        run_env["COEX_LOG_LEVEL"] = "DEBUG"
        run_env["PATH"] = (
            f"./conda.{sname}/bin:"
            + subprocess.check_output("echo $PATH", shell=True, env=None).decode()
        )

        subprocess.check_call(
            f"conda create --yes -p ./conda.{sname} {' '.join(deps)}",
            shell=True,
            cwd=tmp_path,
        )

        # Execution of unzipped .coex dumps proper versions.
        result = subprocess.check_output(
            "./python.coex dump_version.py", shell=True, cwd=tmp_path, env=run_env
        )

        assert json.loads(result) == _test_versions

        unpacked_result = subprocess.check_output(
            "python python.coex.unzipped dump_version.py",
            shell=True,
            cwd=tmp_path,
            env=run_env,
        )

        assert json.loads(unpacked_result) == _test_versions


def test_example_archive(tmp_path: pathlib.Path):
    """Test README.md example with embedded entrypoint."""
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

    # Unzip for filesystem execution
    subprocess.check_output(
        ["unzip", "./dump_version.coex", "-d", "dump_version.coex.unzipped"],
        cwd=tmp_path,
    )

    for sname, deps in _bootstrap_run_envs.items():
        # Execute in clean running environment
        run_env = {}
        run_env["COEX_LOG_LEVEL"] = "DEBUG"
        run_env["PATH"] = (
            f"./conda.{sname}/bin:"
            + subprocess.check_output("echo $PATH", shell=True, env=None).decode()
        )

        subprocess.check_call(
            f"conda create --yes -p ./conda.{sname} {' '.join(deps)}",
            shell=True,
            cwd=tmp_path,
        )

        # Direct execution as .coex dumps proper versions.
        result = subprocess.check_output(
            "./dump_version.coex", shell=True, cwd=tmp_path, env=run_env
        )

        assert json.loads(result) == _test_versions

        # Execution of unzipped .coex dumps proper versions.
        unpacked_result = subprocess.check_output(
            "python dump_version.coex.unzipped", shell=True, cwd=tmp_path, env=run_env
        )

        assert json.loads(unpacked_result) == _test_versions
