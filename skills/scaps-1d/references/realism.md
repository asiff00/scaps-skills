# Realism

A SCAPS result is a statement about a parameter set, not about a material. Check the parameters before the result.

## Hard limits

- Efficiency, Voc, Jsc and FF must stay below the Shockley-Queisser (detailed-balance) values for the absorber band gap under the same spectrum. Anything above is unphysical, whatever the paper it came from.
- The radiative Voc deficit Eg/q - Voc is at least about 0.25 V at 300 K (0.24 V at 1.1 eV, 0.30 V at 2.0 eV).
- Reference values, AM1.5G, 300 K:

| Eg (eV) | Jsc (mA/cm2) | Voc (V) | FF (%) | PCE (%) |
|---|---|---|---|---|
| 1.00 | 48.2 | 0.765 | 85.6 | 31.5 |
| 1.12 | 43.8 | 0.877 | 87.0 | 33.4 |
| 1.34 | 35.0 | 1.082 | 88.9 | 33.7 |
| 1.50 | 28.9 | 1.231 | 90.0 | 32.0 |
| 1.60 | 25.4 | 1.324 | 90.5 | 30.4 |
| 2.00 | 14.5 | 1.699 | 92.2 | 22.7 |

Values computed from the ASTM G173 global spectrum; they agree with Rühle, Solar Energy 130 (2016) 139, doi:10.1016/j.solener.2016.02.015. The SCAPS AM1.5G file differs slightly; the tools compute the limit for the spectrum actually used.

- Practical ceilings: perovskite single junctions about 31 % with demonstrated lifetimes and surface velocities (Diekmann et al., Solar RRL 5 (2021) 2100219, doi:10.1002/solr.202100219); crystalline silicon 29.4 % (Richter et al., IEEE J. Photovolt. 3 (2013) 1184, doi:10.1109/JPHOTOV.2013.2270351).

## Why SCAPS results come out too high

Saidarsan et al. reviewed more than 250 perovskite SCAPS studies (Solar Energy Materials and Solar Cells 279 (2025) 113230, doi:10.1016/j.solmat.2024.113230). The recurring causes:

- No radiative or Auger recombination. SCAPS defaults both to zero; with low defect densities nothing limits Voc. Set the radiative coefficient of the absorber (MAPbI3 about 1e-10 cm^3/s order; silicon 1.8e-15 cm^3/s per the SCAPS manual) or the Shockley-Queisser option `numerical.Shockley-Queisser_limit.always` (SCAPS 3.3.11 and later).
- Absorber defect densities of 1e9 to 1e13 cm^-3 in polycrystalline films. Capacitance and SCLC methods cannot resolve such low densities in thin films (Ravishankar, Unold and Kirchartz, Science 371 (2021) eabd8014, doi:10.1126/science.abd8014; Le Corre et al., ACS Energy Letters 6 (2021) 1087, doi:10.1021/acsenergylett.0c02599). Single crystals reach 1e9 to 1e10 cm^-3; films are usually 1e14 to 1e16.
- Excessive doping of transport layers and absorbers chosen to maximise efficiency rather than taken from measurement.
- Ideal heterointerfaces without interface defects. The front interface defect density is often the critical parameter (Minemoto and Murata, J. Appl. Phys. 116 (2014) 054505, doi:10.1063/1.4891982).
- The default sqrt(hv - Eg) absorption with a large prefactor instead of measured absorption data; SCAPS also neglects interference and scattering.

Kirk analysed a SCAPS study reporting a 1.1 eV CIGS cell at 40.7 % with Voc above Eg/q and peak efficiency at the highest defect density (RSC Advances 14 (2024) 31655, doi:10.1039/D4RA03002H). Any of these signs is disqualifying.

## Checks to run on every device

| Check | Action |
|---|---|
| Absorber radiative and Auger coefficients are zero and the S-Q option is off | set a radiative coefficient or the S-Q option |
| Absorber bulk defect density below 1e13 cm^-3 | justify with measurement or raise |
| Charged deep defects above 10 % of the doping | expect compensation and a changed space charge |
| Heterointerface without interface defects | add one (1e10 to 1e12 cm^-2 is typical) |
| Interface defect density given in cm^-3 | SCAPS interface densities are per cm^2 |
| Conduction band cliff below -0.2 eV or spike above +0.4 eV at the absorber | review electron affinities and their sources |
| Flat-band contacts and Rs = 0, Rsh infinite | add work functions and parasitic resistances when comparing with real cells |
| Default absorption model for indirect or band-tail absorbers (Si, Sb2Se3, CZTS) | use an absorption file |
| Temperature other than 300 K | set Eg and mobilities for that temperature |
| NC 2.2e18 and NV 1.8e19 on non-CIGS layers | values copied from the CIGS baseline |
| NC or NV outside about 1e16 to 1e21 cm^-3 | implies an impossible effective mass; a small value suppresses ni and lifts Voc above the detailed-balance limit |
| Peak efficiency at the largest defect density in a sweep | the defect type, level or cross sections are wrong |

The optimum conduction band offset at an absorber/buffer interface is usually 0 to +0.4 eV: a cliff raises interface recombination, a large spike blocks current (Minemoto et al., Solar Energy Materials and Solar Cells 67 (2001) 83, doi:10.1016/S0927-0248(00)00266-X).

## Numerical warnings from the SCAPS manual

- Recombination must exist somewhere or the solver does not converge.
- A neutral defect does not exist in reality; it only sets lifetimes.
- No interference, scattering or reflection at internal interfaces; no transients, so no ion migration or hysteresis.
- Multi-junction stacks rarely converge directly; split them (see workflows).
- Negative capacitance or capacitance rising with frequency signals a numerical problem.
- To fix convergence: raise the iteration limit, then relax clamping and stop criteria, then add working point steps; start voltage sweeps at the working point voltage.

## What a credible report contains

SCAPS version and non-default numerical settings; the full parameter table with the source of every value; interface defects with density (cm^-2), cross sections and energy reference; contacts, Rs and Rsh; spectrum, temperature and absorption data source; J-V figures of merit; QE with integrated Jsc; band diagram; recombination profile where relevant; comparison with the detailed-balance limit, the record cell of that technology, and ideally a fit to measured devices (Krückemeier et al., Advanced Energy Materials 10 (2020) 1902573, doi:10.1002/aenm.201902573).
