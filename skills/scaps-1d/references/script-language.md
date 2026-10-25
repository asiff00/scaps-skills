# SCAPS script language

One command per line: `verb key [value]`. The installed version ships its full command list as `scriptdescriptionXXXX.txt` in the SCAPS folder (semicolon separated); keys are written with dots in scripts.

## Structure of a run

```
set quitscript.quitSCAPS            // exit when done (needed headless)
set errorhandling.overwritefile     // errors to SCAPSErrorLogFile.log, never dialogs
clear all
load definitionfile my cell.def     // bare names, resolved in SCAPS def/
set layer1.thickness 0.6
clear actions
action light
action workingpoint.temperature 300
action iv.doiv
action iv.startV 0
action iv.stopV 1.2
action iv.increment 0.02
calculate singleshot
save results.iv my run.iv          // written to SCAPS results/
```

## Commands that matter

| Purpose | Commands |
|---|---|
| Device | `set layerN.{thickness,Eg,chi,epsilon,NC,NV,mun,mup,vthn,vthp,NA,ND,radiative,Augern,Augerp,name}` |
| Structure | `set layerN.{add_default,duplicate,remove,split.leftfraction}` |
| Grading and absorption | `set layerN.Eg.file x.grd`, `set layerN.composition.file`, `set layerN.absorption.file x.abs`, `set layerN.absorptionmodel.power1.{on,alpha1,Eg1,exponent1}` |
| Bulk defects | `set layerN.defectM.{Ntotal,Et,Echar,capture_cross_section.electron,capture_cross_section.hole}`; type flags `singledonor`, `singleacceptor`, `neutral`, `amphoteric`; distribution flags `singlelevel`, `uniform`, `gauss`, `CBtail`, `VBtail`; reference flags `aboveEV`, `aboveEi`, `belowEC`; `duplicate`, `remove` |
| Interfaces | `set interfaceK.IFdefectM.{Ntotal,Et,...}`, `set interfaceK.{1,2,3}_default_IFdefect(s)`, `set interfaces_all.inactive` |
| Contacts | `set contactleft.{flatband.off,workfunction,Sn,Sp,opticalfilter.file}`, same for `contactright` |
| Parasitics | `set external.{Rs,Rsh,Gsh}` (ohm cm2, S/cm2) |
| Illumination | `action light`/`dark`, `set illumination.fromleft`/`fromright`, `load spectrumfile`, `action intensity.ND`, `action spectrumcutoff.{on,shortlambda,longlambda}` |
| Generation | `action generation_specified`, `action generationfile x.gen`, `action generationmodel.gaussian.*` |
| Working point | `action workingpoint.{temperature,voltage,frequency,numberofpoints}` |
| Measurements | `action iv.*`, `cv.*`, `cf.{startf,stopf,points.per.decade}`, `qe.{startlambda,stoplambda,increment}` |
| Numerics | `set numerical.Shockley-Queisser_limit.{never,if_needed,always}`, `set numerical.recalculate_mesh.*`, `set numerical.CV-analysis.*` |
| Calculate | `calculate singleshot`, `calculate batch`, `calculate recorder`, `calculate equilibrium_only` |
| Save | `save results.{iv,cv,cf,qe,eb,genrec,ac}`, `save settings.definitionfile x.def` |
| Scripting | `get`, `math`, `loop start/stop`, `run script`, `run dll scapsuserfunction` |

## Gotchas

- Contacts: `contactleft`/`contactright`. The manual's `leftcontact` is rejected.
- `clear actions` resets the working point to 300 K, 0 V, 1 MHz.
- IV and CV sweeps hold at most 201 points.
- `save results.ac` needs a preceding C-V or C-f calculation.
- `eb` and `genrec` saved after a sweep describe its last point; calculate again with no measurement to get them at the working point.
- After several calculations without `clear simulations`, a result file holds every block.
- A script cannot add the first bulk defect to a layer (`add_default` needs an existing defect).
- `set interfaceK.IFdefectM.capture_cross_section.*` changes only the right-hand side of the interface; `scaps_create_device`, `scaps_edit_device` and `scripts/scaps.py` also write the left-hand side.
- Multivalent defects: a set command applies to all levels.
- Missing input files are silently replaced by models; always read the error log.
- `show scriptvariables` and `errorhandling.toscreen` open dialogs that block headless runs; the tools remove them.
- `run system` executes host commands; the tools reject it.
