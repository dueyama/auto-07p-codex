---
name: analyze-bifurcations-with-auto
description: Install, diagnose, verify, and run AUTO-07p locally for continuation and bifurcation analysis of algebraic systems and ordinary differential equations. Use when Codex is asked to install AUTO or AUTO-07p in a project, repair an AUTO environment, run an existing AUTO problem, create a reproducible AUTO workspace, inspect AUTO output files, or analyze folds, Hopf points, periodic orbits, and other bifurcations.
---

# Analyze bifurcations with AUTO

Keep AUTO project-local. Do not modify shell startup files or place upstream
AUTO source under Git control.

## Install or diagnose

1. Locate the target project root. Default to the current working directory.
2. Run `python3 <skill-dir>/scripts/autoctl.py --project-root <root> doctor`.
3. If required system tools are absent, report the exact missing tools. Obtain
   approval before using a system package manager.
4. Run the `install` command when the user requested installation. It retrieves
   the pinned official AUTO-07p commit, builds it under `.auto/versions/`, and
   switches `.auto/current` only after the build succeeds.
5. Run `verify`. Do not claim success from clone, build, PID, or exit status
   alone. Require the generated environment, executable, Python interface, and
   smoke-test artifacts to pass.
6. Report `.auto/install-manifest.json`, the resolved commit, compiler version,
   and verification result.

Read [installation.md](references/installation.md) when dependencies are
missing, a build fails, or the user asks how installation works.

## Run AUTO

Prefer the target repository's `bin/auto-codex` wrapper when it exists.
Otherwise run the controller's `where` command and load the generated
`cmds/auto.env.sh` only for the child process.

Create each analysis under a dedicated run directory. Preserve model inputs,
constants, invoked commands, logs, and output files together. Never overwrite a
user's existing `b.*`, `s.*`, `d.*`, or `fort.*` files without explicit
authorization.

Read [analysis-workflow.md](references/analysis-workflow.md) before generating
or modifying an AUTO model, choosing continuation constants, or interpreting
special points.

## Visualize every accepted run

Treat visualization as a core deliverable, not an optional post-processing
step. After an accepted run:

1. Select axes from the scientific request and available AUTO columns. Confirm
   ambiguous parameter indices instead of guessing.
2. Run `scripts/plot_bifurcation.py <run-dir>/b.<name>`.
3. Generate PNG and SVG for viewing, tidy CSV for reuse, and JSON containing
   provenance and special points.
4. Draw stable segments as solid and unstable segments as dashed. Distinguish
   equilibrium and periodic-orbit families.
5. Mark and label detected special points such as `HB`, `LP`, `BP`, `PD`, and
   `TR`.
6. Display the generated figure in Codex and link the durable output files.
7. Check the figure against the CSV and AUTO labels before describing it.

For a periodic branch, consider an amplitude plot and a period plot when both
materially help. Do not collapse disconnected branches into one polyline.

## Validate results

Check all of the following:

- AUTO produced the expected branch and solution files.
- Diagnostic output contains no convergence or compilation failure.
- The requested continuation parameter and bounds match the generated inputs.
- Detected special-point labels support the stated conclusion.
- Plots and summaries are derived from the saved output, not from expectations.

State uncertainty when the requested bifurcation was not found in the explored
range. Suggest a bounded next experiment instead of silently widening a scan.

## Safety

- Treat AUTO equation files as executable native code because they are compiled.
- Inspect unfamiliar model sources before building them.
- Keep downloads, builds, and generated outputs inside the target project.
- Refuse an uninstall target unless it resolves exactly to `<project>/.auto`.
- Do not redistribute or commit the upstream AUTO-07p source.
