#!/usr/bin/env python3
"""Install and verify a project-local AUTO-07p build."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence


UPSTREAM_URL = "https://github.com/auto-07p/auto-07p.git"
PINNED_COMMIT = "44cc1c42a888179bdbd608a40613caee9cbc4675"
REQUIRED_TOOLS = ("git", "make", "gfortran")


class AutoCtlError(RuntimeError):
    """Expected controller failure."""


def project_root(value: str | None) -> Path:
    root = Path(value or os.getcwd()).expanduser().resolve()
    home = Path.home().resolve()
    if root == Path(root.anchor) or root == home:
        raise AutoCtlError(f"refusing broad project root: {root}")
    if not root.is_dir():
        raise AutoCtlError(f"project root is not a directory: {root}")
    return root


def paths(root: Path) -> dict[str, Path]:
    auto_dir = root / ".auto"
    return {
        "root": root,
        "auto": auto_dir,
        "versions": auto_dir / "versions",
        "current": auto_dir / "current",
        "manifest": auto_dir / "install-manifest.json",
        "log": auto_dir / "install.log",
    }


def run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    log_file: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as stream:
            stream.write(f"$ {' '.join(command)}\n")
            stream.write(result.stdout)
            if result.stdout and not result.stdout.endswith("\n"):
                stream.write("\n")
    if result.returncode:
        tail = "\n".join(result.stdout.splitlines()[-20:])
        raise AutoCtlError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{tail}"
        )
    return result


def tool_record(name: str) -> dict[str, str | None]:
    executable = shutil.which(name)
    record: dict[str, str | None] = {"path": executable, "version": None}
    if not executable:
        return record
    result = subprocess.run(
        [executable, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    record["version"] = result.stdout.splitlines()[0] if result.stdout else "unknown"
    return record


def build_environment() -> dict[str, str]:
    env = os.environ.copy()
    if platform.system() != "Darwin" or env.get("SDKROOT"):
        return env
    xcrun = shutil.which("xcrun")
    if not xcrun:
        return env
    result = subprocess.run(
        [xcrun, "--sdk", "macosx", "--show-sdk-path"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    sdkroot = result.stdout.strip()
    if result.returncode == 0 and Path(sdkroot).is_dir():
        env["SDKROOT"] = sdkroot
    return env


def fortran_probe() -> tuple[bool, str]:
    compiler = shutil.which("gfortran")
    if not compiler:
        return False, "gfortran not found"
    with tempfile.TemporaryDirectory(prefix="autoctl-fortran-") as directory:
        probe_dir = Path(directory)
        source = probe_dir / "probe.f90"
        source.write_text(
            "program probe\n"
            "  use, intrinsic :: iso_c_binding\n"
            "  print *, command_argument_count()\n"
            "end program probe\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [compiler, "-o", str(probe_dir / "probe"), str(source)],
            cwd=probe_dir,
            env=build_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    detail = result.stdout.strip()
    return result.returncode == 0, detail


def doctor_data(root: Path) -> dict[str, object]:
    tools = {name: tool_record(name) for name in (*REQUIRED_TOOLS, "gcc")}
    missing = [name for name in REQUIRED_TOOLS if not tools[name]["path"]]
    if not tools["gcc"]["path"] and not shutil.which("clang"):
        missing.append("C compiler")
    fortran_ok, fortran_detail = fortran_probe()
    if tools["gfortran"]["path"] and not fortran_ok:
        missing.append("working Fortran 2003 compiler")
    p = paths(root)
    return {
        "project_root": str(root),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "tools": tools,
        "missing": missing,
        "fortran_link_probe": {
            "ok": fortran_ok,
            "detail": fortran_detail,
            "sdkroot": build_environment().get("SDKROOT"),
        },
        "installed": p["manifest"].is_file() and p["current"].exists(),
    }


def print_doctor(root: Path, *, as_json: bool) -> int:
    data = doctor_data(root)
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Project: {data['project_root']}")
        print(f"Platform: {data['platform']}")
        print(f"Python: {data['python']}")
        tool_data = data["tools"]
        assert isinstance(tool_data, dict)
        for name, record in tool_data.items():
            assert isinstance(record, dict)
            mark = "ok" if record["path"] else "missing"
            detail = record["version"] or ""
            print(f"{name}: {mark} {detail}".rstrip())
        print(f"AUTO installed: {'yes' if data['installed'] else 'no'}")
        if data["missing"]:
            missing = data["missing"]
            assert isinstance(missing, list)
            print("Missing: " + ", ".join(missing))
    return 1 if data["missing"] else 0


def validate_ref(ref: str) -> str:
    lowered = ref.lower()
    if len(lowered) != 40 or any(c not in "0123456789abcdef" for c in lowered):
        raise AutoCtlError("--ref must be a full 40-character Git commit")
    return lowered


def resolved_commit(source: Path, log_file: Path) -> str:
    return run(
        ("git", "rev-parse", "HEAD"), cwd=source, log_file=log_file
    ).stdout.strip()


def build_is_complete(source: Path) -> bool:
    return (
        (source / "bin" / "auto").is_file()
        and (source / "cmds" / "auto.env.sh").is_file()
        and any((source / "lib").glob("*.o"))
    )


def build_version(root: Path, ref: str, *, keep_failed: bool) -> Path:
    p = paths(root)
    p["versions"].mkdir(parents=True, exist_ok=True)
    p["log"].write_text("", encoding="utf-8")
    destination = p["versions"] / ref

    reuse_checkout = False
    if destination.exists():
        if build_is_complete(destination):
            commit = resolved_commit(destination, p["log"])
            if commit == ref:
                return destination
        if (destination / ".git").is_dir():
            commit = resolved_commit(destination, p["log"])
            if commit == ref:
                reuse_checkout = True
        if not reuse_checkout:
            raise AutoCtlError(
                f"incomplete or mismatched version directory exists: {destination}"
            )

    if not reuse_checkout:
        destination.mkdir()
    try:
        if not reuse_checkout:
            run(("git", "init"), cwd=destination, log_file=p["log"])
            run(
                ("git", "remote", "add", "origin", UPSTREAM_URL),
                cwd=destination,
                log_file=p["log"],
            )
            run(
                ("git", "fetch", "--depth", "1", "origin", ref),
                cwd=destination,
                log_file=p["log"],
            )
            run(
                ("git", "checkout", "--detach", "FETCH_HEAD"),
                cwd=destination,
                log_file=p["log"],
            )
        env = build_environment()
        run(("./configure",), cwd=destination, env=env, log_file=p["log"])
        # AUTO's upstream Makefiles omit some Fortran module dependencies.
        # A parallel build can compile user_c.f90 before support.mod exists.
        run(("make",), cwd=destination, env=env, log_file=p["log"])
        if resolved_commit(destination, p["log"]) != ref:
            raise AutoCtlError("checked-out AUTO commit does not match requested ref")
        if not build_is_complete(destination):
            raise AutoCtlError("build omitted AUTO object library or environment files")
        return destination
    except Exception:
        if not keep_failed and destination.exists():
            shutil.rmtree(destination)
        raise


def activate(root: Path, version: Path, ref: str) -> dict[str, object]:
    p = paths(root)
    temp_link = p["auto"] / ".current.tmp"
    if temp_link.exists() or temp_link.is_symlink():
        temp_link.unlink()
    temp_link.symlink_to(Path("versions") / ref)
    temp_link.replace(p["current"])

    manifest: dict[str, object] = {
        "schema_version": 1,
        "upstream": UPSTREAM_URL,
        "commit": ref,
        "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "project_root": str(root),
        "auto_dir": str(version),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "tools": {
            name: tool_record(name) for name in (*REQUIRED_TOOLS, "gcc")
        },
        "verified": False,
    }
    p["manifest"].write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def install(root: Path, ref: str, *, keep_failed: bool) -> int:
    data = doctor_data(root)
    missing = data["missing"]
    assert isinstance(missing, list)
    if missing:
        raise AutoCtlError("missing required tools: " + ", ".join(missing))
    version = build_version(root, ref, keep_failed=keep_failed)
    activate(root, version, ref)
    print(f"AUTO-07p installed: {version}")
    print(f"Commit: {ref}")
    print(f"Manifest: {paths(root)['manifest']}")
    return 0


def load_manifest(root: Path) -> dict[str, object]:
    manifest_path = paths(root)["manifest"]
    if not manifest_path.is_file():
        raise AutoCtlError("AUTO is not installed; run the install command")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutoCtlError(f"invalid install manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise AutoCtlError("invalid install manifest: expected an object")
    return data


def auto_environment(source: Path) -> dict[str, str]:
    env = build_environment()
    env["AUTO_DIR"] = str(source)
    env["PATH"] = f"{source / 'cmds'}:{source / 'bin'}:{env.get('PATH', '')}"
    python_path = f"{source / 'python'}:{source / 'python' / 'auto'}"
    if env.get("PYTHONPATH"):
        python_path = f"{python_path}:{env['PYTHONPATH']}"
    env["PYTHONPATH"] = python_path
    return env


def evaluate_smoke(log_text: str, error_text: str) -> dict[str, int]:
    combined = f"{log_text}\n{error_text}"
    failures = (
        "AUTO Runtime Error",
        "Error running AUTO",
        "Traceback (most recent call last)",
    )
    found_failures = [item for item in failures if item in combined]
    if found_failures:
        raise AutoCtlError("AUTO smoke test failed: " + ", ".join(found_failures))
    if "Demo ab is done" not in log_text:
        raise AutoCtlError("AUTO smoke test did not complete the ab demo")
    counts = {
        "hopf_points": log_text.count(" HB "),
        "limit_points": log_text.count(" LP "),
    }
    if not counts["hopf_points"] or not counts["limit_points"]:
        raise AutoCtlError("AUTO smoke test omitted expected HB or LP points")
    return counts


def run_smoke_test(root: Path, source: Path, env: dict[str, str]) -> dict[str, object]:
    p = paths(root)
    p["auto"].mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".smoke-", dir=p["auto"]))
    log_base = staging / "autoctl-smoke"
    try:
        run(
            (
                sys.executable,
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(source / 'test')!r}); "
                    "import test; "
                    "raise SystemExit(test.test("
                    "['ab'], versions=['07p'], "
                    f"log_file={str(log_base)!r}, parse=False))"
                ),
            ),
            cwd=staging,
            env=env,
            log_file=p["log"],
        )
        trial_log = Path(f"{log_base}07p")
        error_log = Path(f"{log_base}07perrors")
        if not trial_log.is_file() or not error_log.is_file():
            raise AutoCtlError(f"AUTO smoke test omitted logs in {staging}")
        log_text = trial_log.read_text(encoding="utf-8", errors="replace")
        error_text = error_log.read_text(encoding="utf-8", errors="replace")
        counts = evaluate_smoke(log_text, error_text)
        destination = p["auto"] / "smoke"
        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
        return {
            "demo": "ab",
            **counts,
            "log": str(destination / trial_log.name),
            "diagnostics": str(destination / error_log.name),
        }
    except Exception:
        print(f"AUTO smoke-test artifacts preserved at: {staging}", file=sys.stderr)
        raise


def verify(root: Path) -> int:
    p = paths(root)
    manifest = load_manifest(root)
    current = p["current"].resolve()
    expected = p["versions"] / str(manifest["commit"])
    if current != expected.resolve():
        raise AutoCtlError(f"current link does not match manifest: {current}")

    required = (
        current / "bin" / "auto",
        current / "cmds" / "auto.env.sh",
        current / "python" / "auto",
    )
    missing = [str(item) for item in required if not item.exists()]
    if missing:
        raise AutoCtlError("installation is incomplete: " + ", ".join(missing))

    env = auto_environment(current)
    probe = run(
        (
            sys.executable,
            "-c",
            "import auto; print('__AUTOCTL_MODULE__=' + auto.__file__)",
        ),
        cwd=root,
        env=env,
        log_file=p["log"],
    )
    module_lines = [
        line.removeprefix("__AUTOCTL_MODULE__=")
        for line in probe.stdout.splitlines()
        if line.startswith("__AUTOCTL_MODULE__=")
    ]
    if len(module_lines) != 1:
        raise AutoCtlError("could not identify the imported AUTO Python module")
    imported_from = Path(module_lines[0]).resolve()
    if current not in imported_from.parents:
        raise AutoCtlError(f"Python imported AUTO from unexpected path: {imported_from}")

    commit = resolved_commit(current, p["log"])
    if commit != manifest["commit"]:
        raise AutoCtlError("installed source commit differs from manifest")

    smoke = run_smoke_test(root, current, env)
    manifest["verified"] = True
    manifest["verified_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest["python_module"] = str(imported_from)
    manifest["smoke_test"] = smoke
    p["manifest"].write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("AUTO-07p verification passed")
    print(f"Commit: {commit}")
    print(f"Python module: {imported_from}")
    print(f"Smoke test: {smoke['demo']} ({smoke['log']})")
    return 0


def where(root: Path) -> int:
    manifest = load_manifest(root)
    print(manifest["auto_dir"])
    return 0


def uninstall(root: Path, *, yes: bool) -> int:
    target = paths(root)["auto"].resolve()
    expected = (root / ".auto").resolve()
    if target != expected:
        raise AutoCtlError(f"refusing unexpected uninstall target: {target}")
    if not yes:
        raise AutoCtlError("uninstall requires --yes")
    if target.exists():
        shutil.rmtree(target)
        print(f"Removed: {target}")
    else:
        print("AUTO is not installed")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Manage a project-local AUTO-07p installation."
    )
    result.add_argument(
        "--project-root",
        help="Target project directory (default: current working directory)",
    )
    commands = result.add_subparsers(dest="command", required=True)
    doctor_parser = commands.add_parser("doctor", help="Check required tools")
    doctor_parser.add_argument("--json", action="store_true")
    install_parser = commands.add_parser("install", help="Build pinned AUTO-07p")
    install_parser.add_argument("--ref", default=PINNED_COMMIT)
    install_parser.add_argument("--keep-failed", action="store_true")
    commands.add_parser("verify", help="Verify the active installation")
    commands.add_parser("where", help="Print the active AUTO directory")
    uninstall_parser = commands.add_parser(
        "uninstall", help="Remove only this project's .auto directory"
    )
    uninstall_parser.add_argument("--yes", action="store_true")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = project_root(args.project_root)
        if args.command == "doctor":
            return print_doctor(root, as_json=args.json)
        if args.command == "install":
            return install(
                root,
                validate_ref(args.ref),
                keep_failed=args.keep_failed,
            )
        if args.command == "verify":
            return verify(root)
        if args.command == "where":
            return where(root)
        if args.command == "uninstall":
            return uninstall(root, yes=args.yes)
        raise AutoCtlError(f"unknown command: {args.command}")
    except AutoCtlError as exc:
        print(f"autoctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
