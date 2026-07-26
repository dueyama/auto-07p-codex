from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "skills"
    / "analyze-bifurcations-with-auto"
    / "scripts"
    / "autoctl.py"
)
SPEC = importlib.util.spec_from_file_location("autoctl_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
AUTOCTL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUTOCTL)

PLOT_MODULE_PATH = (
    ROOT
    / "skills"
    / "analyze-bifurcations-with-auto"
    / "scripts"
    / "plot_bifurcation.py"
)
PLOT_SPEC = importlib.util.spec_from_file_location(
    "plot_bifurcation_under_test", PLOT_MODULE_PATH
)
assert PLOT_SPEC and PLOT_SPEC.loader
PLOT = importlib.util.module_from_spec(PLOT_SPEC)
PLOT_SPEC.loader.exec_module(PLOT)


class AutoCtlTests(unittest.TestCase):
    def test_validate_ref_accepts_full_sha(self) -> None:
        value = "a" * 40
        self.assertEqual(AUTOCTL.validate_ref(value), value)

    def test_validate_ref_rejects_branch(self) -> None:
        with self.assertRaises(AUTOCTL.AutoCtlError):
            AUTOCTL.validate_ref("master")

    def test_project_root_rejects_home(self) -> None:
        with self.assertRaises(AUTOCTL.AutoCtlError):
            AUTOCTL.project_root(str(Path.home()))

    def test_paths_are_project_local(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            values = AUTOCTL.paths(root)
            self.assertEqual(values["auto"], root / ".auto")
            self.assertEqual(values["manifest"], root / ".auto/install-manifest.json")

    def test_source_scripts_alone_are_not_a_complete_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "bin").mkdir()
            (source / "bin/auto").write_text("#!/bin/sh\n", encoding="utf-8")
            (source / "cmds").mkdir()
            (source / "cmds/auto.env.sh").write_text("", encoding="utf-8")
            self.assertFalse(AUTOCTL.build_is_complete(source))

    def test_load_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            auto_dir = root / ".auto"
            auto_dir.mkdir()
            expected = {"commit": "a" * 40}
            (auto_dir / "install-manifest.json").write_text(
                json.dumps(expected), encoding="utf-8"
            )
            self.assertEqual(AUTOCTL.load_manifest(root), expected)

    def test_evaluate_smoke_requires_completed_branch_with_special_points(self) -> None:
        result = AUTOCTL.evaluate_smoke(
            "  1  28  HB  7\n  1  32  LP  8\nDemo ab is done\n",
            "compiler warning only\n",
        )
        self.assertEqual(result, {"hopf_points": 1, "limit_points": 1})

    def test_evaluate_smoke_rejects_runtime_error(self) -> None:
        with self.assertRaises(AUTOCTL.AutoCtlError):
            AUTOCTL.evaluate_smoke(
                "Demo ab is done\n  1  28  HB  7\n  1  32  LP  8\n",
                "AUTO Runtime Error: Error running AUTO\n",
            )

    def test_doctor_reports_missing_required_tool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with mock.patch.object(
                AUTOCTL,
                "tool_record",
                side_effect=lambda name: {
                    "path": None if name == "gfortran" else f"/bin/{name}",
                    "version": None if name == "gfortran" else "test version",
                },
            ), mock.patch.object(
                AUTOCTL,
                "fortran_probe",
                return_value=(False, "gfortran not found"),
            ):
                data = AUTOCTL.doctor_data(root)
            self.assertIn("gfortran", data["missing"])

    def test_uninstall_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / ".auto").mkdir()
            with self.assertRaises(AUTOCTL.AutoCtlError):
                AUTOCTL.uninstall(root, yes=False)
            self.assertTrue((root / ".auto").exists())


class PlotBifurcationTests(unittest.TestCase):
    def test_stability_segments_preserve_transition_point(self) -> None:
        self.assertEqual(
            PLOT.stability_segments([-3, 5], 5),
            [(0, 3, True), (2, 5, False)],
        )

    def test_point_stability_uses_latest_segment_at_transition(self) -> None:
        self.assertEqual(
            PLOT.point_stability([-3, 5], 5),
            [True, True, False, False, False],
        )


if __name__ == "__main__":
    unittest.main()
