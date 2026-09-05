# AUTO analysis workflow

## Inputs

Identify the equations, state variables, free parameters, initial solution,
continuation direction, parameter bounds, and requested special points before
running a continuation.

Obtain these from the supplied model, demo constants, and conversation first.
For a named demo, use its defaults unless the user requests changes. For a new
model, state reasonable numerical defaults and proceed when the scientific
intent is clear; ask when equations or the parameter mapping are ambiguous.

Use a copied run directory rather than editing a user's accepted model in
place. Record the relationship between parameter indices (`PAR(i)`) and
scientific parameter names.

## Outputs

AUTO commonly saves:

- `b.<name>`: branch and bifurcation diagram data
- `s.<name>`: labeled solutions
- `d.<name>`: diagnostic data
- `fort.7`, `fort.8`, `fort.9`: unsaved equivalents during a run

Keep the three streams together. A branch file without its diagnostics is not
enough to establish convergence.

## Interpretation

Tie every reported special point to its AUTO type label and parameter values.
Examples include `LP` for a limit point and `HB` for a Hopf point. Do not infer
a periodic branch merely from an equilibrium stability change; continue from
the saved Hopf solution and verify the periodic-orbit output.

Report the explored range and step controls. Absence of a detected special
point within one numerical scan is not proof of global absence.

## Visualization contract

Produce all four views from the same parsed `b.*` source:

- PNG for immediate review
- SVG for publication-quality editing
- tidy CSV with branch, point, stability, type, label, x, and y
- JSON with source path, selected axes, counts, special points, and outputs

Use solid lines for stable segments and dashed lines for unstable segments.
Use separate visual identity for equilibria and periodic orbits. Mark special
points with both shape and text so the plot does not depend on color alone.

Never connect separate AUTO branches. Preserve branch order, stability
transitions, and the parameter/value pair attached to every annotation.

Check that every intended branch has the selected axis columns: the bundled
plotter skips branches that lack them. Do not describe a partial plot as the
whole computed structure. Verify that stability information is applicable to
the problem; missing or unsupported stability information is not evidence of
instability.
