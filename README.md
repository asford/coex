# COEX

[![Build Status](https://img.shields.io/azure-devops/build/asewallford/ce058e44-7619-4a00-8e79-8ab4b3166157/1/master?label=pipelines)](https://dev.azure.com/asewallford/asewallford/_build/latest?definitionId=1&branchName=master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


coex is a utility for generating coex (COnda EXecutable) files, which are
self-contained, executable conda environments. coex is an expansion of the
ideas in [pex](https://github.com/pantsbuild/pex) and makes application
deployment as simple as `cp`. `coex` executables are hermetic and
language agnostic, allowing applications to use arbitrary conda-based
environments with minimal run-time external dependencies.

## TLDR

Package an environment `.yml`...

```bash
$ cat > coex_environment.yml <<EOF
dependencies:
  - python=3.7.4
  - numpy=1.16.4
EOF
```

...with a `python` entrypoint:

```bash
$ python -m coex create -f coex_environment.yml --entrypoint python -o python.coex
```

...and execute:

```bash
$ ls -Ggh python.coex
-rwxr--r-- 1 245M Sep  1 20:22 python.coex

$ ./python.coex
Python 3.7.4 (default, Aug 13 2019, 20:35:49)
[GCC 7.3.0] :: Anaconda, Inc. on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import numpy
>>> numpy.version.version
'1.16.4'
```

... or with a user script entrypoint:

```bash
$ (cat > echo_versions && chmod +x echo_versions) <<EOF
#!/usr/bin/env python
import sys
import numpy
print(sys.version)
print(numpy.version.version)
EOF

$ python -m coex create -f coex_environment.yml --entrypoint ./echo_versions -o echo_versions.coex ./echo_versions
```
...and execute:

```bash
$ ./echo_versions.coex
3.7.4 (default, Aug 13 2019, 15:17:50)
[Clang 4.0.1 (tags/RELEASE_401/final)]
1.16.4
```

## Installation

~~It's recommended to install `coex` in the root conda environment - the
`conda coex` command will then be available in all sub-environments.~~

### ~~From source:~~

~~coex is available on github and can be installed from source:
`pip install git+https://github.com/asford/coex.git`~~

## FAQs

### How does it work?

coex produces executable archives that self-extract, setup an conda
environment, and launch a specified application entrypoint. At build-time
coex uses Conda's solver to convert an environment specification into
a target package list. It then compresses these packages, application
files, and minimal bootstrap components into
a [PEP-441](https://legacy.python.org/dev/peps/pep-0441/)-style executable
archive compatible with any python interpreter. At run time, coex uses the
host interpreter to quickly unpack bootstrap components and install
packages into a conda environment, it then activates this environment and
executes the entrypoint program.

By pre-calculating the target environment and using fast zstd compression,
coex is able to quickly unpack the target environment at run time. This
results in an short, but unavoidable, startup delay.

By including bootstrap components in a self-extracting archive, coex files
depend only on a system `python` (2.7+ or 3) and minimal system libraries.
The application is executed entirely via hermetically included components.
For example, a full pytorch & python3.7 based coex application can be
executed in a host environment depending only the system `python2.7` and
cuda driver.

### What does it support?

`coex` strives to be *fast*, *practical* and *universal*. It's intended to
handle a single opinionated use case extremely well, not supplant existing
solutions.

This currently includes:

* Prefix handling during package install.
* Platform-specific packages.
* `noarch:python` packages.
* Build and execute on linux and macos.
* Package and execute application and data.

This doesn't, but should, include:

* `post-link` package scripts.

This doesn't include:

* Cross platform executables. coex files are akin to static binaries built
  for a target platform.
* Cross-executable resource sharing. coex files are hermetic, replicating
  required dependencies at the cost of increased package size.

### Why not use...

* containers?

  [Docker](https://www.docker.com/) and container-based deployment tools
  have many advantages over coex, but have a hard dependency on
  a container build process and runtime. coex can quickly capture a conda
  environment to be executed anywhere, depending only on system libraries
  and a minimal python (2.7+) installation. coex files can be trivially
  encapsulated for deployment onto container-based architectures.

* XAR?

  [XAR](https://github.com/facebookincubator/xar) has superior (a) startup
  time and (b) cross-package data sharing for deploying multiple files as
  a self-contained executable, but requires a SquashFS filesystem driver.
  This prevents deployment to container-based architectures and
  environments without support for the XAR driver. coex can execute
  anywhere with a minimal python (2.7+) installation.

* PEX?

  [PEX](https://github.com/pantsbuild/pex) and
  [subpar](https://github.com/google/subpar) are tightly focused on
  packaging python executables and do not provide isolation from the
  system python environment. coex supports any application language, as
  long as your dependencies can be captured via conda.

* conda-pack?

  [conda-pack](https://conda.github.io/conda-pack/) packages conda
  environments as redistributable archives, rather than creating
  self-contained executables. coex executables can be unpacked for
  environment redeployment is a similar fashion.

## Development

coex uses [tox](https://tox.readthedocs.io/en/latest/) and
[tox-conda](https://github.com/tox-dev/tox-conda) to manage test and
development environments. First, install `conda>=4.6` , `tox>=13.3` and
`tox-conda>=0.2.0` by whatever means necessary (eg. `conda env update -n
base -f tox.environment.yml`).

Initialize the dev env under `.tox/dev` and register pre-commit hooks via:

```bash
$ tox -e dev
```

The dev env can be activated via `conda activate .tox/dev`, or via
[`direnv`](https://direnv.net/) and the included `.envrc` file.

Tests under `tests` are run via `pytest` in the dev env, the full multi-version
test matrix is run via `tox`.
