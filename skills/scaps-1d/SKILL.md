---
name: scaps-1d
description: Use this skill whenever a solar cell must be treated as a semiconductor device rather than a product or material. That covers any request to simulate, sweep, optimize, plot, explain or sanity-check a perovskite or thin-film cell (MAPbI3, FAPbI3, CIGS, CdTe, CZTS, Sb2Se3, others): best absorber thickness, doping or defect density, ETL/HTL electron affinity, band offsets and Voc, band diagrams, J-V, QE or C-V curves, temperature or light-intensity dependence, fitting to measured curves, and whether a reported SCAPS efficiency is credible. Always use it when SCAPS, SCAPS-1D, a layer stack such as FTO/TiO2/absorber/HTL/Au, or .def/.material files appear. It provides the SCAPS runner, literature parameters and Shockley-Queisser realism checks, so load it before answering, even conceptual questions. Not for DFT, optics-only modelling (transfer matrix, FDTD), efficiency-chart summaries, module/system design, or measured-data analysis without a device model.
---

# SCAPS-1D

SCAPS-1D solves the one-dimensional semiconductor equations for a layered solar cell. Results are only as credible as the parameters: most published SCAPS efficiencies above 30 % come from missing recombination, not good design. Treat realism as part of every answer.

## Choose how to run SCAPS

1. **MCP tools present** (`scaps_simulate`, `scaps_batch`, ...): use them. They validate every key against the installed SCAPS, run jobs, and return analysis and realism checks.
2. **No MCP tools, shell available**: use `scripts/scaps.py` (Python 3.10+, standard library only): describe, simulate, batch, fit, create, edit, run, parse, absorption files and detailed-balance limits. Run `python3 scripts/scaps.py --help`; `create --help` shows the JSON device spec. It finds SCAPS in the usual install locations, Wine prefixes included, or uses `SCAPS_HOME`; on Linux SCAPS runs under Wine and Xvfb. Suggest the scaps-mcp server for background jobs and plots.
3. **Neither**: write the SCAPS script or the parameter table for the user to run in the SCAPS GUI, and parse the result files they send back (`scripts/scaps.py parse`, and `describe` on a .def file, work without SCAPS).

## Workflow

1. **Start from a device.** List definitions, describe the one requested, and restate the stack (layers from the back contact, thickness, Eg, chi, doping, defects, interface defects, contacts). Ask for a `.def` file if the user describes a published cell; sharing the definition is the norm in SCAPS work.
2. **Check before simulating.** Read the device checks; fix or flag missing radiative recombination, defect-free absorbers, ideal interfaces, band spikes or cliffs and flat-band contacts. See `references/realism.md`.
3. **Simulate the baseline.** Use the defaults first (AM1.5G, 300 K, light J-V from 0 V); then add QE, C-V or profiles as the question needs.
4. **Vary one thing at a time** with a batch; for interactions use a grid of at most two variables. Keep IV sweeps at or below 201 points.
5. **Fit before you predict** whenever measured curves exist: fit the few parameters the data constrain (defect density, doping, a thickness) and report the remaining ones as assumptions.
6. **Report** results with units, the parameters changed, the SCAPS version and the checks. Never present a result above the Shockley-Queisser limit, or with an 'error' check, as achievable.

## Key rules

- Script units: thickness um, doping and bulk defect density cm^-3, interface defect density cm^-2, mobility cm^2/Vs, velocity cm/s, cross section cm^2, energies eV. Definition files store SI; input files use SI except nm and um.
- Layers, defects and interfaces count from 1; layer 1 touches the left (back) contact, and light enters from the right unless `illumination.fromleft` is set.
- Contacts are `contactleft` and `contactright`; the manual's `leftcontact` fails in scripts. A work function only applies after `contactX.flatband.off`.
- A script cannot create the first bulk defect of a layer; start from a definition that has one, or let `scaps_create_device` or `scripts/scaps.py create` seed it.
- SCAPS scales only NC, NV and thermal velocity with temperature; set Eg(T) and mobilities yourself in temperature studies.
- The tools calculate `eb` profiles (bands, carriers, field, currents, generation and recombination rates) and `genrec` profiles (defect occupation) at the working point voltage; in a hand-written script a profile saved after a sweep describes the sweep's last point. `ac` profiles need a C-V or C-f run.
- Grading laws, multilevel defect levels and the GUI curve fitter have no script commands; use grading files, fitting tools, or the GUI.

## References

- `references/workflows.md`: recipes for common studies (thickness, doping, defects, band alignment, temperature, intensity, C-V and C-f analysis, EBIC, fitting, tandem, bifacial, metastability).
- `references/realism.md`: checks, detailed-balance limits and literature on unrealistic SCAPS results.
- `references/parameters.md`: literature parameter ranges for common absorbers and transport layers, with their spread.
- `references/script-language.md`: the script commands that matter, with gotchas.
- `references/file-formats.md`: `.def`, `.material`, `.abs`, `.spe`, `.gen`, `.ftr`, `.grd` and measurement files.
