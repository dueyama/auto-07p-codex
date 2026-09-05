---
name: analyze-bifurcations-with-auto
description: Install, diagnose, verify, and run AUTO-07p locally for continuation and bifurcation analysis of algebraic systems and ordinary differential equations. Use when Codex is asked to install AUTO or AUTO-07p in a project, repair an AUTO environment, run an existing AUTO problem, create a reproducible AUTO workspace, inspect AUTO output files, or analyze folds, Hopf points, periodic orbits, and other bifurcations.
---

# Analyze bifurcations with AUTO

Keep AUTO project-local. Do not modify shell startup files or place upstream
AUTO source under Git control.

Follow the user's requested scope and output preferences. A simple request such
as "run the ab demo and show its bifurcation diagram" is enough: use the demo's
supplied model and constants, run it, and show the plot. Ask only when missing
information materially changes the scientific question; do not turn available
defaults into a questionnaire. Diagnosis alone does not authorize installation
or changes to the environment.

In commands below, `<skill-dir>` is the absolute directory containing this
`SKILL.md`, not the user's working directory. `<project-root>` is the target
project. Resolve and quote these paths before running commands; the target
project need not contain this repository's scripts or wrapper.

## Install or diagnose

1. Locate the target project root. Default to the current working directory.
2. Run `python3 "<skill-dir>/scripts/autoctl.py" --project-root "<project-root>" doctor`.
3. If required system tools are absent, report the exact missing tools. Obtain
   approval before using a system package manager.
4. Run the `install` command when the user requested installation. It retrieves
   the pinned official AUTO-07p commit, builds it under `.auto/versions/`, and
   switches `.auto/current` only after the build succeeds.
5. After installation or a rebuild, run `verify`. Do not claim success from clone, build, PID, or exit status
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
2. Run the bundled plotter with explicit paths:

   ```bash
   python3 "<skill-dir>/scripts/plot_bifurcation.py" "<run-dir>/b.<name>" \
     --auto-dir "<project-root>/.auto/current" --output-dir "<run-dir>/plots"
   ```

   Set `--x` and `--y` to the chosen columns. Parsing saved results does not
   require rebuilding AUTO or running an unrelated smoke test.
3. Generate PNG and SVG for viewing, tidy CSV for reuse, and JSON containing
   provenance and special points.
4. Draw stable segments as solid and unstable segments as dashed. Distinguish
   equilibrium and periodic-orbit families.
5. Mark and label detected special points such as `HB`, `LP`, `BP`, `PD`, and
   `TR`.
6. Display the generated figure in Codex using an absolute local image path
   and link the durable output files. A file path alone is not a displayed plot.
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
- Keep AUTO downloads and builds under the target project's `.auto/`. Default
  analysis outputs to a dedicated project run directory; honor an explicitly
  requested output or temporary-storage location.
- Refuse an uninstall target unless it resolves exactly to `<project>/.auto`.
- Do not redistribute or commit the upstream AUTO-07p source.
