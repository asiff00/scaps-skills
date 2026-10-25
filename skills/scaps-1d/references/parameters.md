# Parameters

Starting values from widely used sources. Many SCAPS papers copy each other; check the original source and prefer measured values for the actual film. Ranges marked *varies* differ by more than a factor of two between papers.

Units: Eg and chi in eV, densities in cm^-3, mobilities in cm^2/Vs.

## Absorbers

| Material | Eg | chi | eps_r | NC / NV | mu_n / mu_p | Doping | Notes |
|---|---|---|---|---|---|---|---|
| CIGS (baseline) | 1.15 | 4.5 | 13.6 | 2.2e18 / 1.8e19 | 100 / 25 | NA 2e16 | Gaussian midgap donor 1e14; Gloeckler, PhD thesis, Colorado State University, 2005 |
| CdTe (baseline) | 1.5 | 4.4 | 9.4 | 8e17 / 1.8e19 | 320 / 40 | NA 2e14 | Nt 2e14; CdS/CdTe conduction band offset -0.1 eV with CdS chi 4.5; same source |
| MAPbI3 | about 1.59 | 3.9 to 4.36 *varies* | 6.5 (optical) to 25 (static) *varies* | about 2e18 / 2e19 | 15 to 40 | near intrinsic | photoemission EA 4.36, IE 5.93 (Tao et al., Nat. Commun. 10 (2019) 2560); IE in the literature spans 5.1 to 6.65 |
| FAPbI3 | 1.51 | about 4.0 to 4.74 *varies* | about 6.6 | | | | EA about 0.3 eV larger than MAPbI3 (Tao 2019) |
| Sb2Se3 | 1.04 indirect, 1.17 direct | | 18 (2 MHz), 14.3 (optical) | | mu_p 0.7 to 2.6, mu_n above 17 | | tau about 67 ns, L about 0.3 um, Nt about 1.3e15; transport is anisotropic, which 1D cannot capture (Chen et al., Front. Optoelectron. 10 (2017) 18) |
| CZTS | 1.5 | 4.5 | 10 | | 100 / 20 in many SCAPS papers | NA 1e16 | measured CZTSSe mobility 0.5 to 1.3 and tau about 7 ns; band tails limit Voc (Gokmen et al., Appl. Phys. Lett. 103 (2013) 103506); SCAPS literature is optimistic |
| Si | 1.12 | 4.05 | 11.7 | 2.8e19 / 3.1e19 | 1400 / 450 (low doping) | | NV per Green, J. Appl. Phys. 67 (1990) 2944; ni 9.65e9 (Altermatt, J. Appl. Phys. 93 (2003) 1598) |

## Transport and window layers

Two widely copied SCAPS tables disagree in places (Hossain et al., ACS Omega 7 (2022) 43210; and a 2023 RSC Advances FACsPb(IBr)3 study). Pairs below are "first table / second table".

| Material | Eg | chi | eps_r | mu | Doping | Notes |
|---|---|---|---|---|---|---|
| TiO2 | 3.2 | 4.0 / 4.1 | 9 | mu_n 20 | ND 9e16 / 1e18 | |
| SnO2 | 3.6 / 3.5 | 4.0 | 9 | mu_n 15 to 100 | ND 1e17 / 1e15 | NC 2.2e18 / 2.2e17 |
| ZnO | 3.3 | 4.0 / 4.1 | 9 | mu_n 100 | ND 1e18 | ZnO/CdS offset -0.2 eV in the CIGS baseline |
| CdS | 2.4 | 4.18 to 4.2; 4.5 in the CdTe baseline | 10 | | ND 1e17 to 1e18 | acceptor traps 1e18 in the CIGS baseline |
| PCBM | 2.0 | 3.9 / 4.2 | 3.9 | 0.2 | | NC = NV 2.5e21 |
| C60 | 1.7 | 3.9 | | mu_n 0.08 | | |
| Spiro-OMeTAD | 3.0 / 2.9 | 2.2 | 3 | mu_p 2e-3 / 1e-4 | NA 1e18 to 1e20 | measured mu_p 1.6e-4 undoped, 1.6e-3 Li-doped (Snaith and Grätzel, Appl. Phys. Lett. 89 (2006) 262114) |
| PEDOT:PSS | 1.6 | 3.4 | | 0.045 | | one source only |
| NiOx | 3.8 | 1.46 | | | | one source only |
| CuSCN | 3.6 | 1.7 | | 100 / 25 | | one source only |
| Cu2O | 2.17 | 3.2 / 3.4 | | mu_p 80 / 8600 | | 8600 is unrealistic; epitaxial films give 40 to 60 |

## Interfaces and contacts

- Interface defect densities: 1e10 to 1e12 cm^-2, capture cross sections 1e-15 to 1e-19 cm^2.
- Contact surface recombination: 1e7 cm/s for ohmic metal contacts; reduce only for passivated or selective contacts.
- Back-contact barriers: the CdTe baseline uses a deliberate 0.4 eV barrier; otherwise keep majority-carrier barriers below about 0.3 eV.

## Recombination coefficients

- Radiative: MAPbI3 about 1e-10 cm^3/s order (intrinsic k2 reported as 6.8e-10); Si 1.8e-15 cm^3/s (SCAPS manual). When unknown, use the SCAPS Shockley-Queisser option, which sets the radiative limit of each layer.
- Auger (Si): about 1e-30 to 1e-31 cm^6/s.
