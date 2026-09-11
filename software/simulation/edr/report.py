"""
Human-readable crash report generator.

Turns a stored event (metadata + analytics + integrity) into a plain-text
report an investigator or examiner can read directly.
"""

from datetime import datetime, timezone


def build_report(event_meta, analytics, integrity, pre_summary):
    a = analytics
    lines = []
    w = lines.append

    w("=" * 62)
    w("   ENHANCED EVENT DATA RECORDER — CRASH REPORT")
    w("=" * 62)
    w(f"Event ID        : {event_meta['event_id']}")
    w(f"Scenario        : {event_meta.get('scenario', 'n/a')}")
    ts = datetime.fromtimestamp(event_meta.get("rtc_epoch", 0), tz=timezone.utc)
    w(f"Time (UTC)      : {ts.strftime('%Y-%m-%d %H:%M:%S')}")
    w(f"Location        : {event_meta.get('latitude')}, {event_meta.get('longitude')}")
    w(f"Trigger(s)      : {', '.join(event_meta.get('triggers', []))}")
    w("")

    w("-" * 62)
    w("   CRASH ANALYSIS")
    w("-" * 62)
    w(f"Severity            : {a['severity']}")
    w(f"Impact direction    : {a['impact_direction']}  (PDOF {a['pdof_deg']} deg)")
    w(f"Peak acceleration   : {a['peak_g']} g")
    w(f"Delta-V             : {a['delta_v_kmph']} km/h")
    w(f"Crash Severity Index: {a['csi']} / 100")
    w(f"Speed at impact     : {a['speed_at_impact_kmph']} km/h")
    w(f"Rollover            : {'YES' if a['rollover'] else 'no'} "
      f"(max roll {a['max_roll_deg']} deg)")
    w("")

    w("-" * 62)
    w("   PRE-CRASH (last 5 s before impact)")
    w("-" * 62)
    w(f"Entry speed         : {pre_summary['entry_speed']} km/h")
    w(f"Min speed           : {pre_summary['min_speed']} km/h")
    w(f"Max braking         : {pre_summary['max_brake']} %")
    w(f"Max steering        : {pre_summary['max_steer']} deg")
    w(f"ABS engaged         : {'yes' if pre_summary['abs'] else 'no'}")
    w("")

    w("-" * 62)
    w("   FORENSIC INTEGRITY")
    w("-" * 62)
    w(f"Flash checksum      : {integrity['sha256'][:32]}...")
    w(f"Checksum verified   : {'PASS' if integrity['verified'] else 'FAIL'}")
    w(f"Write-protect lock  : {'ENGAGED' if integrity['locked'] else 'open'}")
    w(f"Parameters locked   : {integrity['param_count']} of 40")
    w(f"Samples captured    : {integrity['sample_count']}")
    w("=" * 62)
    return "\n".join(lines)
