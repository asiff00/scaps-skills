# File formats

All SCAPS files are plain text in the Windows-1252 encoding. Input files use SI units except wavelength (nm) and position (um). Lines that do not start with two numbers are comments.

| File | Folder | Content |
|---|---|---|
| `.def` | def | Problem definition: numerics, contacts, layers, defects, interfaces, working point. Values in SI (m, m^-3, m^2/Vs, m/s, m^2). Shared between researchers as "the device". |
| `.material` | materials | One layer's material without name, thickness, doping and defects, plus its absorption file name. Loaded per layer in the GUI; values in GUI units (cm based). |
| `.abs` | absorption | Absorption: wavelength (nm), alpha (1/m). Interpolated logarithmically. alpha = 4 pi k / lambda. |
| `.spe` | spectrum | Spectrum: wavelength (nm), power in the interval around it (W/m2); the sum is the incident power. At most 2500 lines. Comment lines start with `>`. |
| `.gen` | generation | Generation profile: position (um), G (1/m3/s). |
| `.ftr` | filter | Optical filter: wavelength (nm), transmission or reflection (%). |
| `.grd` | grading | Two columns: position (um, or relative 0..1, or composition) and value. Header lines `position: relative`, `interpolation: linear` or `logarithmic`, `range: shared over adjacent layers`. |
| `.iv`, `.cv`, `.cf`, `.qe` | results, measurements | Results: header lines, tab-separated table, J-V files end with Voc, Jsc, FF, eta, V_MPP, J_MPP. Measurements: header code words `area`, `temperature`, `bias`, `frequency`, `Pin`, `dark`, `units:`; columns I-V V (V), I (mA); C-V V, C (nF), G (S); C-f f (Hz), C, G; QE lambda (nm), QE (%). |
| `.eb` results | results | Spatial profiles: `bulk` table (x, bands, quasi-Fermi levels, carriers, charge, field, currents, generation and recombination rates, cumulative currents) and `interface` table. |
| `.gen` results (genrec) | results | Occupation of every defect level against position. Not a generation input file despite the extension. |
| `.act`, `.sbf`, `.srf`, `.scaps` | def and others | Action lists, batch and recorder settings, complete SCAPS states made in the GUI. |
| `.script` | script | SCAPS scripts. |

`.def` and `.material` files often reference `.abs` and `.grd` files by name only; when such a file is missing SCAPS silently falls back to a model and only logs it.
