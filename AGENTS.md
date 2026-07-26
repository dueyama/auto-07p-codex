# AutoOnCodex instructions

- Use the Codex in-app browser for browser work. Do not use Chrome.
- For AUTO-07p installation, diagnosis, execution, or bifurcation analysis, read
  `skills/analyze-bifurcations-with-auto/SKILL.md` completely before acting.
- Install AUTO-07p only inside the target project under `.auto/`.
- Do not edit a user's shell startup files. Use the repository wrapper or the
  generated AUTO environment file for each process.
- Treat a successful build or exit status as insufficient verification. Run the
  smoke test and inspect its generated AUTO output.
- Do not commit `.auto/` or generated analysis runs.
