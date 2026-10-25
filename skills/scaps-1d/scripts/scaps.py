#!/usr/bin/env python3
"""Run, parse and check SCAPS-1D simulations from the command line. Output is JSON on stdout.

  scaps.py status
  scaps.py describe DEF                     device in script units, band offsets, realism checks
  scaps.py simulate DEF [options]           --measure iv,qe --profile eb --set KEY=VALUE --action KEY=VALUE
  scaps.py batch DEF KEY=V1,V2,... [...]    grid over set or action keys (--zip pairs them)
  scaps.py run SCRIPT                       run a SCAPS script with safety checks
  scaps.py parse FILE [FILE ...]            parse result or measurement files, no SCAPS needed
  scaps.py sq EG [EG ...]                   Shockley-Queisser limits under the SCAPS AM1.5G spectrum
  scaps.py absorption NAME DATA [options]   .abs file from alpha or k data (nm, um or eV), e.g. ellipsometry
  scaps.py edit BASE NEW [options]          --set KEY=VALUE --material N=FILE --numerics KEY=VALUE
  scaps.py create NAME SPEC.json            new device: layers, defects, interface defects, contacts
  scaps.py fit DEF --vary KEY=MIN:MAX[:log]  fit --measured KIND=FILE[:dark][:log] curves, or --maximize,
                                            --minimize or --target METRIC[=VALUE]

SCAPS is found in the usual install locations, including Wine prefixes; set SCAPS_HOME to use another folder.
parse, describe of a .def given by path, and absorption --output work without SCAPS.
"""

from __future__ import annotations

import argparse
import asyncio
import filecmp
import json
import math
import re
import shutil
import signal
import sys
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scapskit import checks, devices, inputs
from scapskit.catalog import Catalog
from scapskit.config import ConfigError, Settings, load_settings
from scapskit.optimize import Variable, fit_error, nelder_mead
from scapskit.parsing import (
    DEFINITION_UNITS,
    Result,
    measurement_scales,
    parse_definition,
    parse_material,
    parse_result,
    parse_spectrum,
)
from scapskit.physics import Spectrum, band_offsets, integrated_jsc, mott_schottky, sq_limit
from scapskit.runner import ENCODING, RunOutcome, run
from scapskit.scripts import (
    ScriptError,
    Simulation,
    Validator,
    check_filename,
    check_targets,
    edit_script,
    user_script,
)

METRICS = {
    "Voc": "voc_v",
    "Jsc": "jsc_ma_cm2",
    "FF": "ff_pct",
    "eta": "eta_pct",
    "V_MPP": "vmpp_v",
    "J_MPP": "jmpp_ma_cm2",
}
KEY_COLUMNS = {
    "iv": ("v(V)", "jtot(mA/cm2)"),
    "qe": ("lambda(nm)", "QE(%)"),
    "cv": ("v(V)", "C(nF/cm2)", "G(S/cm2)"),
    "cf": ("f(Hz)", "C(nF/cm2)", "G(S/cm2)"),
}
DEFAULT_SPECTRUM = "AM1_5G 1 sun.spe"
METRIC_KEYS = ("eta_pct", "voc_v", "jsc_ma_cm2", "ff_pct")
CREATE_SPEC = """\
JSON spec with values in script units; flags take null:
{
 "layers": [
  {"name": "absorber", "thickness": 0.5, "Eg": 1.55, "chi": 3.9, "NA": 1e15, "radiative": 1e-10,
   "defects": [{"neutral": null, "gauss": null, "Et": 0.6, "Ntotal": 1e14}]},
  {"name": "window", "material": "CIGSe.material", "thickness": 0.05, "ND": 1e18}
 ],
 "interfaces": {"1": [{"Ntotal": 1e10}]},
 "left_contact": {"workfunction": 5.1},
 "right_contact": {"Sn": 1e5},
 "options": {"numerical.Shockley-Queisser_limit.always": null},
 "numerics": {"maxiter": 2000}
}
Layers count from the left (back) contact; a material file applies first and explicit keys override it."""


class Failure(Exception):
    pass


def settings(args: argparse.Namespace) -> Settings:
    try:
        s = load_settings()
    except ConfigError as error:
        raise Failure(str(error)) from None
    if args.out:
        s = replace(s, runs_dir=Path(args.out).expanduser())
    return replace(s, timeout=args.timeout) if args.timeout else s


def read(path: Path) -> str:
    return path.read_text(encoding=ENCODING, errors="replace")


def validator(s: Settings) -> Validator:
    return Validator(Catalog.for_home(s.home, s.exe.stem))


def spectrum(s: Settings, name: str | None) -> Spectrum | None:
    path = s.home / "spectrum" / (name or DEFAULT_SPECTRUM)
    return Spectrum.from_bins(parse_spectrum(read(path))) if path.is_file() else None


def metrics(result: Result) -> dict | None:
    return {key: result.metrics.get(name) for name, key in METRICS.items()} if result.metrics else None


def curve(result: Result, measurement: str | None) -> dict | None:
    table = result.table
    if table is None:
        return None
    wanted = KEY_COLUMNS.get(measurement or "", ())
    keep = [table.columns.index(c) for c in wanted if c in table.columns] or list(range(len(table.columns)))
    return {"columns": [table.columns[i] for i in keep], "rows": [[r[i] for i in keep] for r in table.rows]}


def definition(s: Settings, name: str) -> str:
    """Return a definition name inside SCAPS def/, copying a .def given by path if needed."""
    source = Path(name).expanduser()
    if source.suffix.lower() == ".def" and source.is_file() and source.parent.resolve() != (s.home / "def"):
        target = s.home / "def" / source.name
        if target.exists() and not filecmp.cmp(source, target, shallow=False):
            raise Failure(f"a different {source.name} already exists in SCAPS def/; rename your file")
        shutil.copyfile(source, target)
        return source.name
    candidate = name if name.lower().endswith(".def") else f"{name}.def"
    for path in (s.home / "def").iterdir():
        if path.name.lower() == candidate.lower():
            return path.name
    raise Failure(f"{candidate!r} not found in SCAPS def/")


def value(text: str) -> float | str:
    try:
        return float(text)
    except ValueError:
        return text


def pairs(items: list[str]) -> list[tuple[str, float | str | None]]:
    result = []
    for item in items:
        key, sep, raw = item.partition("=")
        result.append((key.strip(), value(raw.strip()) if sep else None))
    return result


def numbers(items: list[str], flag: str) -> dict[str, float]:
    parsed = {}
    for key, val in pairs(items):
        if not isinstance(val, float):
            raise Failure(f"{flag} expects KEY=NUMBER, got {key}={val}")
        parsed[key] = val
    return parsed


def errors(outcome: RunOutcome) -> list[dict]:
    return [{"command": e.command, "message": e.message} for e in outcome.errors]


def status(outcome: RunOutcome, produced: int, expected: int) -> str:
    if outcome.timed_out:
        return "timed_out"
    return "completed" if produced == expected else "partial" if produced else "failed"


def collect(outcome: RunOutcome, outputs: dict[str, str]) -> dict[str, Result]:
    parsed = {}
    for kind, name in outputs.items():
        path = outcome.files.get(name)
        result = parse_result(read(path)) if path else None
        if result is not None and result.table is not None:
            parsed[kind] = result
    return parsed


def describe(device: dict) -> dict:
    layers = device["layers"]
    for interface in device["interfaces"]:
        left, right = interface["layers"]
        if right <= len(layers):
            interface["band_offsets"] = band_offsets(layers[left - 1], layers[right - 1])
    return {**device, "absorber_layer": checks.absorber_index(device), "checks": checks.device_checks(device)}


def build(args: argparse.Namespace, s: Settings, extra: tuple[str, ...] = ()) -> tuple[Simulation, dict]:
    name = definition(s, args.definition)
    actions = pairs(args.action)
    if args.temperature is not None:
        actions.insert(0, ("workingpoint.temperature", args.temperature))
    if args.voltage is not None:
        actions.insert(0, ("workingpoint.voltage", args.voltage))
    sim = Simulation(
        definition=name,
        measurements=[m.strip() for m in args.measure.split(",") if m.strip()],
        profiles=[p.strip() for p in args.profile.split(",") if p.strip()],
        settings=pairs(args.set),
        actions=actions,
        illumination="dark" if args.dark else "light",
        spectrum=args.spectrum,
    )
    device = parse_definition(read(s.home / "def" / name))
    check_targets(device, [*(k for k, _ in sim.settings), *extra])
    sim.validate(validator(s))
    return sim, device


def analysis(s: Settings, args: argparse.Namespace, device: dict, parsed: dict[str, Result]):
    found: dict = {}
    limit = None
    a = checks.absorber_index(device)
    light = spectrum(s, args.spectrum)
    if a and light and not args.dark and device["layers"][a - 1].get("Eg"):
        limit = sq_limit(light, device["layers"][a - 1]["Eg"], args.temperature or 300.0)
        if limit:
            found["sq_limit"] = asdict(limit)
    if "qe" in parsed and light:
        rows = parsed["qe"].table.rows
        found["qe_jsc_ma_cm2"] = integrated_jsc(light, [r[0] for r in rows], [r[1] for r in rows])
        found["qe_range_nm"] = [rows[0][0], rows[-1][0]]
    if "cv" in parsed:
        table = parsed["cv"].table
        if "C(nF/cm2)" in table.columns and "v(V)" in table.columns:
            ci, vi = table.columns.index("C(nF/cm2)"), table.columns.index("v(V)")
            column = "eps_s to determine N"
            eps = table.rows[0][table.columns.index(column)] if column in table.columns else None
            eps = eps or (device["layers"][a - 1].get("epsilon") if a else None) or 10.0
            reverse = [r for r in table.rows if r[vi] is not None and r[vi] <= 0] or table.rows
            fit = mott_schottky([r[vi] for r in reverse], [r[ci] for r in reverse], eps)
            if fit:
                found["mott_schottky"] = fit
    return found, limit


def cmd_status(args: argparse.Namespace) -> dict:
    s = settings(args)
    catalog = Catalog.for_home(s.home, s.exe.stem)
    return {
        "scaps_version": s.version,
        "executable": s.exe.name,
        "scaps_home": str(s.home),
        "scaps_home_source": s.source,
        "other_installations": [str(p) for p in s.others],
        "wine_prefix": str(s.wineprefix) if s.wineprefix else None,
        "runs_dir": str(s.runs_dir),
        "script_commands": len(catalog.commands) if catalog else 0,
        "definitions": sorted(p.name for p in (s.home / "def").glob("*.def")),
    }


def cmd_describe(args: argparse.Namespace) -> dict:
    path = Path(args.definition).expanduser()
    if not path.is_file():
        s = settings(args)
        path = s.home / "def" / definition(s, args.definition)
    return {"definition": path.name, "units": DEFINITION_UNITS, **describe(parse_definition(read(path)))}


def cmd_simulate(args: argparse.Namespace) -> dict:
    s = settings(args)
    sim, device = build(args, s)
    script, outputs = sim.script(validator(s), "skill")
    outcome = run(s, script, list(outputs.values()))
    parsed = collect(outcome, outputs)
    iv = metrics(parsed["iv"]) if "iv" in parsed else None
    found, limit = analysis(s, args, device, parsed)
    return {
        "run_id": outcome.run_id,
        "run_dir": str(outcome.directory),
        "status": status(outcome, len(parsed), len(outputs)),
        "definition": sim.definition,
        "metrics": iv,
        "analysis": found,
        "files": [outputs[k] for k in parsed],
        "curves": {k: curve(r, k) for k, r in parsed.items()} if args.curves else {},
        "scaps_errors": errors(outcome),
        "checks": checks.device_checks(device) + checks.result_checks(iv, limit, args.temperature),
        "seconds": outcome.seconds,
    }


def cmd_batch(args: argparse.Namespace) -> dict:
    s = settings(args)
    variables = []
    for item in args.variables:
        key, _, raw = item.partition("=")
        variables.append((key.strip(), [value(v) for v in raw.split(",") if v.strip()]))
    sim, device = build(args, s, extra=tuple(k for k, _ in variables))
    v = validator(s)
    script, points, steps = sim.batch_script(v, "skill", variables, "zip" if args.zip else "grid")
    names = [name for step in steps for name in step.values()]
    outcome = run(s, script, names, s.timeout * len(points))
    rows, produced = [], 0
    for point, step in zip(points, steps, strict=True):
        parsed = collect(outcome, step)
        produced += len(parsed)
        rows.append(
            {
                "values": point,
                "metrics": metrics(parsed["iv"]) if "iv" in parsed else None,
                "files": [step[k] for k in parsed],
            }
        )
    found = checks.device_checks(device)
    for key, _ in variables:
        found += checks.sweep_checks(key, [{"value": r["values"][key], "metrics": r["metrics"]} for r in rows])
    return {
        "run_id": outcome.run_id,
        "run_dir": str(outcome.directory),
        "status": status(outcome, produced, len(names)),
        "definition": sim.definition,
        "points": rows,
        "scaps_errors": errors(outcome),
        "checks": found,
        "seconds": outcome.seconds,
    }


def cmd_run(args: argparse.Namespace) -> dict:
    s = settings(args)
    script, outputs, problems, warnings = user_script(
        Path(args.script).read_text(encoding=ENCODING), Catalog.for_home(s.home, s.exe.stem)
    )
    if problems:
        raise Failure("; ".join(problems))
    outcome = run(s, script, outputs)
    files = []
    for name in outputs:
        path = outcome.files.get(name)
        if path:
            result = parse_result(read(path))
            files.append({"file": name, "kind": result.kind, "metrics": metrics(result)})
    return {
        "run_id": outcome.run_id,
        "run_dir": str(outcome.directory),
        "status": status(outcome, len(files), len(outputs)),
        "warnings": warnings,
        "files": files,
        "scaps_errors": errors(outcome),
        "seconds": outcome.seconds,
    }


def cmd_parse(args: argparse.Namespace) -> list[dict]:
    parsed = []
    for name in args.files:
        path = Path(name).expanduser()
        result = parse_result(read(path))
        entry = {"file": path.name, "kind": result.kind, "metrics": metrics(result), "tables": len(result.tables)}
        if args.curves:
            entry["curve"] = curve(result, path.suffix.lstrip(".").lower())
        parsed.append(entry)
    return parsed


def cmd_sq(args: argparse.Namespace) -> dict:
    s = settings(args)
    light = spectrum(s, args.spectrum)
    if light is None:
        raise Failure("spectrum file not found in SCAPS spectrum/")
    limits = []
    for gap in args.band_gaps:
        limit = sq_limit(light, gap, args.temperature or 300.0)
        if limit is None:
            raise Failure(f"no limit for Eg = {gap:g} eV: no photons above the gap")
        limits.append(asdict(limit))
    return {"limits": limits}


def numeric_rows(text: str, columns: tuple[int, int]) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for line in text.splitlines():
        cells = line.replace(",", " ").replace(";", " ").split()
        try:
            row = [float(c) for c in cells]
        except ValueError:
            continue
        if len(row) > max(columns):
            xs.append(row[columns[0]])
            ys.append(row[columns[1]])
    return xs, ys


def cmd_absorption(args: argparse.Namespace) -> dict:
    columns = tuple(int(c) for c in args.columns.split(","))
    if len(columns) != 2:
        raise Failure("--columns takes two zero-based indices, e.g. 0,2")
    x, y = numeric_rows(Path(args.data).read_text(encoding="utf-8", errors="replace"), columns)
    made = inputs.absorption(args.name, x, y, args.quantity, args.note, args.unit)
    target = Path(args.output).expanduser() if args.output else settings(args).home / made.folder / made.name
    if target.exists() and not args.overwrite:
        raise Failure(f"{target.name} already exists; use --overwrite")
    target.write_text(made.text, encoding=ENCODING, errors="replace", newline="")
    return {"file": target.name, "points": made.points, "status": "completed"}


def resolve(s: Settings, folder: str, name: str) -> str | None:
    if (s.home / folder / name).is_file():
        return name
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    return next((p.name for p in (s.home / folder).iterdir() if re.sub(r"[^a-z0-9]", "", p.name.lower()) == key), None)


def material_settings(s: Settings, layer: int, material: str) -> tuple[list, list[str]]:
    name = resolve(s, "materials", material if material.lower().endswith(".material") else f"{material}.material")
    if name is None:
        raise Failure(f"material {material!r} not found in SCAPS materials/")
    parsed = parse_material(read(s.home / "materials" / name))
    assignments = [(f"layer{layer}.{k}", v) for k, v in parsed["properties"].items()]
    notes = []
    source = parsed["absorption"].get("file")
    if source:
        found = resolve(s, "absorption", source)
        if found:
            assignments.append((f"layer{layer}.absorption.file", found))
        else:
            notes.append(f"{name} refers to missing absorption file {source!r}; absorption left unchanged")
    return assignments, notes


def save_definition(s: Settings, script: str, target: str, numerics: dict, assignments: list) -> None:
    path = s.home / "def" / target
    outcome = run(s, script, [])
    if outcome.errors or not path.exists():
        raise Failure("; ".join(f"{e.command}: {e.message}" for e in outcome.errors) or "SCAPS did not save the file")
    text = devices.set_numerics(read(path), numerics) if numerics else read(path)
    text = devices.set_interface_cross_sections(text, devices.interface_cross_sections(assignments))
    path.write_text(text, encoding=ENCODING, newline="")


def cmd_edit(args: argparse.Namespace) -> dict:
    s = settings(args)
    base = definition(s, args.base)
    target = check_filename(args.new, ".def")
    if (s.home / "def" / target).exists() and not args.overwrite:
        raise Failure(f"{target} already exists; use --overwrite")
    assignments, notes = [], []
    for item in args.material:
        layer, sep, material = item.partition("=")
        if not sep or not layer.strip().isdigit():
            raise Failure(f"--material expects LAYER=FILE, got {item!r}")
        loaded, remarks = material_settings(s, int(layer), material.strip())
        assignments += loaded
        notes += remarks
    assignments += pairs(args.set)
    check_targets(parse_definition(read(s.home / "def" / base)), [k for k, _ in assignments])
    numerics = numbers(args.numerics, "--numerics")
    save_definition(s, edit_script(validator(s), base, assignments, target), target, numerics, assignments)
    return {"definition": target, "notes": notes, **describe(parse_definition(read(s.home / "def" / target)))}


def cmd_create(args: argparse.Namespace) -> dict:
    s = settings(args)
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise Failure(f"{args.spec}: {error}") from None
    if not isinstance(spec, dict) or not isinstance(spec.get("layers"), list):
        raise Failure("the spec must be a JSON object with a 'layers' list; see create --help")
    if not all(isinstance(layer, dict) for layer in spec["layers"]):
        raise Failure("each layer must be an object of set-command suffixes")
    if not isinstance(spec.get("interfaces", {}), dict):
        raise Failure("'interfaces' must be an object keyed by interface number")
    target = check_filename(args.name, ".def")
    path = s.home / "def" / target
    if path.exists() and not args.overwrite:
        raise Failure(f"{target} already exists; use --overwrite")
    notes, layers = [], []
    for layer in spec["layers"]:
        if layer.get("material"):
            loaded, remarks = material_settings(s, 1, layer["material"])
            notes += remarks
            layer = {**{k.removeprefix("layer1."): v for k, v in loaded}, **layer}
            layer.pop("material")
        layers.append(layer)
    interfaces = {int(k): v for k, v in spec.get("interfaces", {}).items()}
    contacts = {side: spec[f"{side}_contact"] for side in ("left", "right") if spec.get(f"{side}_contact")}
    v = validator(s)
    devices.validate(layers, interfaces)
    first = devices.layer_script(v, layers, contacts, list(spec.get("options", {}).items()), target)
    second = devices.defect_script(v, target, layers, interfaces)
    save_definition(s, first, target, spec.get("numerics", {}), [])
    seeded = [i for i, layer in enumerate(layers, 1) if layer.get("defects")]
    if seeded or interfaces:
        path.write_text(devices.insert_seed_defects(read(path), seeded), encoding=ENCODING, newline="")
        requested = [
            (f"interface{k}.IFdefect{j}.{key}", value)
            for k, defects in interfaces.items()
            for j, defect in enumerate(defects, 1)
            for key, value in defect.items()
        ]
        save_definition(s, second, target, {}, requested)
    return {"definition": target, "notes": notes, **describe(parse_definition(read(path)))}


FIT_COLUMNS = {"iv": "jtot(mA/cm2)", "qe": "QE(%)", "cv": "C(nF/cm2)", "cf": "C(nF/cm2)"}


def measured_curve(s: Settings | None, kind: str, name: str) -> tuple[list[float], list[float]]:
    """Measured x and y in V/Hz/nm and mA/cm2, nF/cm2 or %, honouring the file's area and units headers."""
    path = Path(name).expanduser()
    if not path.is_file() and s is not None:
        path = s.home / "measurements" / name
    if not path.is_file():
        raise Failure(f"measurement file {name!r} not found")
    text = read(path)
    table = parse_result(text).table
    if table is not None and len(table.columns) >= 2:
        rows = [r for r in table.rows if r[0] is not None and r[1] is not None]
        xs, ys = [r[0] for r in rows], [r[1] for r in rows]
    else:
        xs, ys = numeric_rows(text, (0, 1))
    sx, sy = measurement_scales(text, kind)
    return [x * sx for x in xs], [y * sy for y in ys]


def cmd_fit(args: argparse.Namespace) -> dict:
    s = settings(args)
    space = []
    for item in args.vary:
        key, _, bounds = item.partition("=")
        parts = bounds.split(":")
        if not key or len(parts) not in (2, 3):
            raise Failure(f"--vary expects KEY=MIN:MAX[:log], got {item!r}")
        try:
            space.append(Variable(key, float(parts[0]), float(parts[1]), log=len(parts) > 2 and parts[2] == "log"))
        except ValueError as error:
            raise Failure(f"--vary {item!r}: {error}") from None
    goal, metric, target = "fit", None, None
    if args.maximize or args.minimize:
        goal, metric = ("maximize", args.maximize) if args.maximize else ("minimize", args.minimize)
    elif args.target:
        goal = "target"
        metric, sep, raw = args.target.partition("=")
        if metric not in METRIC_KEYS or not sep:
            raise Failure(f"--target expects METRIC=VALUE with METRIC one of {', '.join(METRIC_KEYS)}")
        try:
            target = float(raw)
        except ValueError:
            raise Failure(f"--target value {raw!r} is not a number") from None
    targets = []
    for item in args.measured:
        kind, _, rest = item.partition("=")
        name, *flags = rest.split(":")
        if kind not in FIT_COLUMNS:
            raise Failure("measured kinds are iv, qe, cv and cf")
        x, y = measured_curve(s, kind, name)
        dark = "dark" in flags or (kind in ("cv", "cf") and "light" not in flags)
        targets.append({"kind": kind, "x": x, "y": y, "log": "log" in flags, "light": not dark})
    if goal == "fit" and not targets:
        raise Failure("give --measured curves, or --maximize, --minimize or --target")
    if goal != "fit":
        targets = [{"kind": "iv", "x": [], "y": [], "log": False, "light": True}]
    groups: dict[bool, list[dict]] = {}
    for t in targets:
        groups.setdefault(t["light"], []).append(t)
    keys = tuple(var.key for var in space)
    sims = {}
    for light, group in groups.items():
        kinds = sorted({t["kind"] for t in group})
        own = [a for a in args.action if a.split(".")[0] not in FIT_COLUMNS or a.split(".")[0] in kinds]
        condition = argparse.Namespace(**{**vars(args), "measure": ",".join(kinds), "dark": not light, "action": own})
        sims[light], device = build(condition, s, extra=keys)
    v = validator(s)
    history = []

    def score(parsed: dict, group: list[dict]) -> float:
        total = 0.0
        for t in group:
            result = parsed.get(t["kind"])
            if result is None or FIT_COLUMNS[t["kind"]] not in result.table.columns:
                return math.inf
            yi = result.table.columns.index(FIT_COLUMNS[t["kind"]])
            rows = result.table.rows
            total += fit_error([r[0] for r in rows], [r[yi] for r in rows], t["x"], t["y"], t["log"])
        return total

    async def evaluate(points: list[list[float]]) -> list[float]:
        values = [[var.from_unit(u) for var, u in zip(space, point, strict=True)] for point in points]
        series = [(var.key, [vals[i] for vals in values]) for i, var in enumerate(space)]
        totals, iv = [0.0] * len(points), [None] * len(points)
        for light, sim in sims.items():
            script, combos, steps = sim.batch_script(v, "fit", series, "zip")
            outcome = run(s, script, [n for step in steps for n in step.values()], s.timeout * len(combos))
            for i, step in enumerate(steps):
                parsed = collect(outcome, step)
                if light and "iv" in parsed:
                    iv[i] = metrics(parsed["iv"])
                if goal == "fit":
                    totals[i] += score(parsed, groups[light]) / len(targets)
        scores = []
        for i, vals in enumerate(values):
            if goal == "fit":
                value = totals[i]
            else:
                m = (iv[i] or {}).get(metric)
                value = math.inf if m is None else {"maximize": -m, "minimize": m}.get(goal, abs(m - (target or 0)))
            history.append({"values": dict(zip(keys, vals, strict=True)), "value": value, "metrics": iv[i]})
            scores.append(value)
        print(f"{len(history)} evaluations, best {min(h['value'] for h in history):.4g}", file=sys.stderr)
        return scores

    start = [0.5] * len(space)
    _, _, count = asyncio.run(nelder_mead(evaluate, start, args.max_evals))
    finite = [h for h in history if math.isfinite(h["value"])]
    if not finite:
        raise Failure("no evaluation produced results; check scaps_errors with a single simulate run")
    best = min(finite, key=lambda h: h["value"])
    return {
        "status": "completed",
        "goal": goal,
        "best": best["values"],
        "best_value": -best["value"] if goal == "maximize" else best["value"],
        "best_metrics": best["metrics"],
        "evaluations": count,
        "checks": checks.device_checks(device),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", help="folder for run outputs (default: SCAPS_RUNS_DIR or the user cache folder)")
    p.add_argument("--timeout", type=float, help="seconds per SCAPS run (default: SCAPS_TIMEOUT or 300)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    d = sub.add_parser("describe")
    d.add_argument("definition")
    d.set_defaults(func=cmd_describe)
    for name, func in (("simulate", cmd_simulate), ("batch", cmd_batch)):
        c = sub.add_parser(name)
        c.add_argument("definition")
        if name == "batch":
            c.add_argument("variables", nargs="+", metavar="KEY=V1,V2")
            c.add_argument("--zip", action="store_true", help="pair the value lists instead of a grid")
        c.add_argument("--measure", default="iv", help="comma-separated: iv, qe, cv, cf")
        c.add_argument("--profile", default="", help="comma-separated: eb, genrec, ac")
        c.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
        c.add_argument("--action", action="append", default=[], metavar="KEY=VALUE")
        c.add_argument("--dark", action="store_true")
        c.add_argument("--temperature", type=float)
        c.add_argument("--voltage", type=float)
        c.add_argument("--spectrum")
        c.add_argument("--curves", action="store_true", help="include key curve columns")
        c.set_defaults(func=func)
    r = sub.add_parser("run")
    r.add_argument("script")
    r.set_defaults(func=cmd_run)
    q = sub.add_parser("parse")
    q.add_argument("files", nargs="+")
    q.add_argument("--curves", action="store_true")
    q.set_defaults(func=cmd_parse)
    g = sub.add_parser("sq")
    g.add_argument("band_gaps", nargs="+", type=float)
    g.add_argument("--temperature", type=float)
    g.add_argument("--spectrum")
    g.set_defaults(func=cmd_sq)
    a = sub.add_parser("absorption")
    a.add_argument("name", help="file name in SCAPS absorption/, .abs is added")
    a.add_argument("data", help="text or CSV file with numeric columns")
    a.add_argument("--columns", default="0,1", help="zero-based x,y columns, e.g. 0,2 for lambda,n,k data")
    a.add_argument("--quantity", default="alpha_per_cm", choices=["alpha_per_cm", "alpha_per_m", "k"])
    a.add_argument("--unit", default="nm", choices=["nm", "um", "ev"], help="unit of the x column")
    a.add_argument("--note", help="source of the data, written as comments")
    a.add_argument("--output", help="write here instead of SCAPS absorption/")
    a.add_argument("--overwrite", action="store_true")
    a.set_defaults(func=cmd_absorption)
    e = sub.add_parser("edit")
    e.add_argument("base")
    e.add_argument("new")
    e.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    e.add_argument("--material", action="append", default=[], metavar="LAYER=FILE")
    e.add_argument("--numerics", action="append", default=[], metavar="KEY=VALUE", help="e.g. maxiter=2000")
    e.add_argument("--overwrite", action="store_true")
    e.set_defaults(func=cmd_edit)
    c = sub.add_parser("create", description=CREATE_SPEC, formatter_class=argparse.RawDescriptionHelpFormatter)
    c.add_argument("name")
    c.add_argument("spec", help="JSON: layers, interfaces, left_contact, right_contact, options, numerics")
    c.add_argument("--overwrite", action="store_true")
    c.set_defaults(func=cmd_create)
    f = sub.add_parser("fit")
    f.add_argument("definition")
    f.add_argument("--vary", action="append", required=True, metavar="KEY=MIN:MAX[:log]")
    f.add_argument("--measured", action="append", default=[], metavar="KIND=FILE[:dark][:log]")
    f.add_argument("--maximize", choices=METRIC_KEYS)
    f.add_argument("--minimize", choices=METRIC_KEYS)
    f.add_argument("--target", metavar="METRIC=VALUE")
    f.add_argument("--max-evals", type=int, default=60)
    f.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    f.add_argument("--action", action="append", default=[], metavar="KEY=VALUE")
    f.add_argument("--temperature", type=float)
    f.add_argument("--voltage", type=float)
    f.add_argument("--spectrum")
    f.set_defaults(func=cmd_fit, profile="")
    return p


def main() -> int:
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal.default_int_handler)
    args = parser().parse_args()
    try:
        output = args.func(args)
    except (Failure, ScriptError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(output, indent=1))
    return 0 if not isinstance(output, dict) or output.get("status", "completed") in ("completed", "partial") else 2


if __name__ == "__main__":
    sys.exit(main())
