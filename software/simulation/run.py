#!/usr/bin/env python3
"""
eEDR command-line interface.

    python run.py list                     list available scenarios
    python run.py run <scenario>           run a scenario, capture any crash
    python run.py run all                  run every scenario in sequence
    python run.py replay <EVENT_ID>        print a stored crash report
    python run.py verify <EVENT_ID>        re-check a stored event's integrity
    python run.py tamper <EVENT_ID>        demo: alter a locked record, show it's caught
    python run.py test                     run the built-in unit tests

By default the code runs against the SIMULATED data source. Swapping to real
hardware is a one-line change (see hardware.py) — the rest of the system is
identical.
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edr import scenarios, config
from edr.hal.simulated import SimulatedDataSource
from edr.recorder import EDRRecorder

WORKDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_output")


def cmd_list(_):
    print("Available scenarios:")
    for name in scenarios.ALL:
        print(f"  - {name}")


def _run_one(name):
    if name not in scenarios.ALL:
        print(f"Unknown scenario '{name}'. Try: python run.py list")
        return
    scenario = scenarios.ALL[name]()
    source = SimulatedDataSource(scenario)
    print("\n" + "#" * 62)
    print(f"#  SCENARIO: {name}")
    print("#" * 62)
    workdir = os.path.join(WORKDIR, name)
    recorder = EDRRecorder(source, workdir, scenario_name=name)
    report = recorder.run()
    if report:
        print("\n" + report)


def cmd_run(args):
    if args.scenario == "all":
        for name in scenarios.ALL:
            _run_one(name)
    else:
        _run_one(args.scenario)


def _event_dir(event_id):
    """Find an event by ID across all scenario workdirs."""
    if not os.path.isdir(WORKDIR):
        return os.path.join(WORKDIR, config.EVENTS_DIR, event_id)
    for scen in os.listdir(WORKDIR):
        cand = os.path.join(WORKDIR, scen, config.EVENTS_DIR, event_id)
        if os.path.isdir(cand):
            return cand
    return os.path.join(WORKDIR, config.EVENTS_DIR, event_id)


def cmd_replay(args):
    path = os.path.join(_event_dir(args.event_id), "report.txt")
    if not os.path.exists(path):
        print(f"No report for {args.event_id}. Have you run a scenario yet?")
        return
    with open(path) as f:
        print(f.read())


def cmd_verify(args):
    from edr.storage import flash as flashmod
    path = os.path.join(_event_dir(args.event_id), config.FLASH_IMAGE)
    if not os.path.exists(path):
        print(f"No flash image for {args.event_id}.")
        return
    ok, checksum = flashmod.verify_crash_image(path)
    print(f"{args.event_id} integrity: {'PASS' if ok else 'FAIL (tampered!)'}")
    print(f"  sha256 = {checksum}")


def cmd_tamper(args):
    """Deliberately alter a locked record to prove tampering is detectable."""
    from edr.storage import flash as flashmod
    path = os.path.join(_event_dir(args.event_id), config.FLASH_IMAGE)
    if not os.path.exists(path):
        print(f"No flash image for {args.event_id}.")
        return
    with open(path) as f:
        image = json.load(f)
    # flip one recorded speed value without updating the checksum
    try:
        image["payload"]["samples"][0]["speed_kmph"] = 999.0
    except (KeyError, IndexError):
        pass
    with open(path, "w") as f:
        json.dump(image, f, indent=2)
    ok, _ = flashmod.verify_crash_image(path)
    print(f"Tampered {args.event_id}: altered a stored speed value.")
    print(f"Integrity check now returns: {'PASS' if ok else 'FAIL — tampering detected'}")


def cmd_test(_):
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(os.path.dirname(__file__), "tests"))
    unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    p = argparse.ArgumentParser(description="Enhanced Event Data Recorder (eEDR)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    r = sub.add_parser("run")
    r.add_argument("scenario", help="scenario name, or 'all'")
    r.set_defaults(func=cmd_run)

    for name in ("replay", "verify", "tamper"):
        sp = sub.add_parser(name)
        sp.add_argument("event_id", help="e.g. EVENT_0001")
        sp.set_defaults(func={"replay": cmd_replay, "verify": cmd_verify,
                              "tamper": cmd_tamper}[name])

    sub.add_parser("test").set_defaults(func=cmd_test)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
