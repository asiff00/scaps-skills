# Workflows

Tool names refer to the scaps-mcp server; the same steps work with `scripts/scaps.py` or as SCAPS scripts.

## Baseline review

1. `scaps_describe_device`: stack, band offsets, checks.
2. `scaps_simulate` with `measurements: ["iv", "qe"]`: metrics, QE-integrated Jsc, detailed-balance limit.
3. Compare Jsc from J-V and from QE; they agree within a few % only when the QE range (`qe_range_nm`) extends past the absorber edge, so set `qe.stoplambda` beyond 1240/Eg nm. Compare Voc with Eg/q - 0.25 V and efficiency with the limit.

## Measured absorption

Prefer measured absorption over the default model. Convert alpha or extinction coefficient k data (wavelength in nm or um, or photon energy in eV) with `scaps_write_data` (`kind: "absorption"`) or `scripts/scaps.py absorption`, then set `layerN.absorption.file`. Record the data source in the note; it becomes the file's comment header.

## New device

`scaps_create_device`, or `scripts/scaps.py create NAME spec.json` (`create --help` prints the spec): layers from the back contact as set-command suffixes with a `defects` list, interface defects by interface number, contacts, options and numerics. Give the absorber a radiative coefficient or the Shockley-Queisser option and each heterojunction an interface defect, then run the baseline review.

## Thickness, doping and defect studies

- `scaps_batch` over one key, e.g. `{"layer1.thickness": [0.2, 0.4, 0.6, 0.8, 1.0]}`; log-spaced values for densities.
- Two-variable maps with `mode: "grid"`; keep the grid below about 100 points.
- Defect tolerance: sweep `layerN.defect1.Ntotal` over 1e12 to 1e17; efficiency must fall with density.
- Doping studies change the depletion width; also look at the band diagram (`profiles: ["eb"]` at the maximum power voltage).

## Band alignment (ETL, HTL, buffer)

- Sweep the electron affinity of the transport layer, `layerN.chi`, which moves the conduction band offset at the absorber interface.
- Read `interfaces[].band_offsets` from the device description; positive steps at the electron contact side are spikes.
- Keep an interface defect at the absorber interface while sweeping, or the cliff penalty disappears.

## Temperature

- `scaps_batch` with `{"workingpoint.temperature": [...], "layer1.Eg": [...], "layer1.mun": [...]}` and `mode: "zip"`, because SCAPS does not scale Eg or mobility with temperature.
- Voc(T) extrapolated to 0 K gives the dominant recombination activation energy; equal to Eg for bulk, lower for interface recombination.

## Intensity (Suns-Voc, ideality)

- Batch over `intensity.ND` (optical density; 1 = 10 % light, negative values concentrate).
- Ideality factor n = (q/kT) dVoc/d ln(intensity).

## C-V and Mott-Schottky

- `scaps_simulate` with `measurements: ["cv"]`, `illumination: "dark"`, `actions: {"cv.startV": -1, "cv.stopV": 0.4, "cv.increment": 0.05}`, `frequency_hz` for the measurement frequency.
- The result includes a Mott-Schottky fit (built-in voltage, doping); the `.cv` file also has SCAPS's own W and Napp columns.
- Epsilon used for Napp: `numerical.CV-analysis.*` settings.

## Admittance spectroscopy (C-f)

- Dark C-f from 1e-2 to 1e7 Hz, 20 points per decade, batch over temperature (300 K down to 150 K).
- Peak of -f dC/df per temperature gives f0(T); an Arrhenius plot of ln(f0/T^2) against 1/kT gives the trap activation energy.

## EBIC and external generation

- Use a Gaussian generation model (`generation_specified`, `generationmodel.gaussian.*` actions) or write a `.gen` file from data, then batch over the beam position. Jsc divided by the ideal light current gives the collection efficiency; the slope of its logarithm gives the diffusion length.

## Fitting measured devices

- `scaps_optimize` with `goal: "fit"` and the measured curves: light J-V, dark J-V (`log: true`), QE, C-V. Each may come from a SCAPS measurement file.
- Fit two to four parameters the data constrain: absorber doping (C-V), absorber defect density (dark J-V, Voc), buffer thickness (QE blue response), interface defect density (Voc, FF).
- Validate on a curve not used in the fit.
- Training case shipped with SCAPS: start from `Numos CIGS baseline.def` and fit CdS thickness, CIGS NA and CIGS Nt to the four `Numos Ex 1` measurement files.

## Optimisation

- `goal: "maximize"` on `eta_pct` over thickness, doping and band offset, within realistic bounds from `parameters.md`.
- Re-check the optimum: an optimum at a bound means the bound decides the answer.

## Tandem cells

Direct simulation of multi-junction stacks rarely converges. SCAPS ships tested scripts for the split approach in its script folder: `tandem mother script.script` and the strategies `adapt generation`, `adapt filters`, `fake partial cells` and `set spectrum`. Adapt one with `scaps_run_script`. The pattern:

1. `load definitionfile` the full stack, `action light`, `load spectrumfile` the evaluation spectrum.
2. `math split_tandem_cell.adapt_generation n1 n2` with n1 + 1 = n2, the layers around the recombination junction; this writes temporary top and bottom cells.
3. `load definitionfile.temporary.top_cell`, `calculate singleshot`, `get iv vt`; the same for `bottom_cell` with `get iv ub`.
4. `math series xyvtub 100` combines the sub-cell curves in series into x (V) and y (J); `math characteristics.all cxy` returns the tandem metrics. `math parallel` works the same way for four-terminal comparisons.

Start the sub-cell J-V near -0.5 V so the series curve covers the operating range. Redo the split after any optical change; the adapt_contact_filters strategy is invalid with internal reflection.

## Bifacial

Simulate front and rear illumination separately (`illumination.fromleft`, `illumination.fromright`) and compare the superposition with a run using the summed generation profile written as a `.gen` file.

## Metastability

Defects with metastable configurations need an initial working point: `initialwp.temperature`, `initialwp.voltage`, `initialwp.light` actions set the state that is frozen before the measurement.
