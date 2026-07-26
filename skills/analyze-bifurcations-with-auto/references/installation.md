# Installation reference

## Layout

The controller uses:

```text
<project>/.auto/
├── current -> versions/<commit>
├── install-manifest.json
└── versions/
    └── <commit>/
```

The upstream checkout is configured and built in place. AUTO's generated
`cmds/auto.env.sh` supplies `AUTO_DIR`, `PATH`, and `PYTHONPATH` to a child
process. Do not source it from a persistent shell startup file.

## Required tools

- Python 3.9 or newer
- Git
- GNU Make
- C compiler
- Fortran compiler (`gfortran`)

On macOS, obtain `gfortran` through a trusted package manager when it is absent.
On Debian-family Linux, the usual packages are `git`, `make`, `gcc`, and
`gfortran`. Ask before installing system packages.

Homebrew provides `gfortran` through its `gcc` formula:

```bash
brew install gcc
```

Run `doctor` after installation. The controller uses the first `gfortran` on
`PATH`, performs a compile-and-link probe with the active macOS SDK, and records
the resolved path and version in the install manifest. Do not remove or replace
another compiler merely to change precedence; adjust `PATH` for the child
process when a specific compiler must be tested.

## Commands

```bash
python3 scripts/autoctl.py doctor
python3 scripts/autoctl.py install
python3 scripts/autoctl.py verify
python3 scripts/autoctl.py where
```

Use `install --ref <full-commit>` only when the user explicitly requests a
different reviewed AUTO revision. Prefer full 40-character commit IDs.

## Failure handling

- Preserve a failed version directory for inspection only when `--keep-failed`
  is supplied; otherwise remove that incomplete directory.
- Never change `.auto/current` until configure and make have succeeded.
- If an existing installation is healthy, make `install` idempotent.
- Record command output in `.auto/install.log`.
- Build AUTO serially because the upstream Makefiles do not fully declare
  Fortran module dependencies required for a reliable parallel build.
- Distinguish missing compiler, configure failure, build failure, and smoke-test
  failure in the final report.
