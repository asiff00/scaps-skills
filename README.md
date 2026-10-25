# scaps-skills

Agent skill for SCAPS-1D, the one-dimensional solar cell simulator of the University of Gent. It teaches an agent to set up, simulate, fit and sanity-check thin-film and perovskite solar cells, and to report results that survive review.

## Contents

- `skills/scaps-1d/SKILL.md`: workflow and rules.
- `skills/scaps-1d/references/`: workflows, realism checks with literature, parameter ranges, script language, file formats.
- `skills/scaps-1d/scripts/scaps.py`: standard-library command line tool to create, edit, simulate, sweep and fit devices with SCAPS headless, write absorption files, parse results and compute detailed-balance limits.
- `evals/`: trigger queries and graded tasks.

## Use

The skill works on its own. With the [scaps-mcp](https://github.com/asiff00/scaps-mcp) server connected it uses the server's tools instead of the bundled script, which adds background jobs, progress reporting, plots and file import.

- Claude Code plugin: `/plugin marketplace add asiff00/scaps-skills`, then `/plugin install scaps@scaps-skills`.
- Plain skill: copy or link `skills/scaps-1d` into a skills folder.

The bundled script needs Python 3.10 or newer. It finds SCAPS in the usual install locations, or uses `SCAPS_HOME` when set; on Linux SCAPS runs under Wine with Xvfb. SCAPS itself is not included; request it from its authors as described on the [SCAPS website](https://scaps.elis.ugent.be/) and follow their conditions of use.

## License

MIT
