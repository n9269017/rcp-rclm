from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
worker_path = root / "scripts/phase17_evaluator_worker.py"
spec = importlib.util.spec_from_file_location("_phase17_worker_diagnostic", worker_path)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

def location(frame):
    path = Path(frame.f_code.co_filename)
    try:
        name = path.resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        name = "<external>/" + path.name
    return {"file": name, "function": frame.f_code.co_name, "line": frame.f_lineno}

def trace(frame, event, arg):
    if frame.f_code is not worker.main.__code__:
        return None
    frame.f_trace_lines = False
    if event == "exception":
        exc_type, exc, tb = arg
        frames = []
        while tb is not None and len(frames) < 24:
            item = location(tb.tb_frame)
            item["line"] = tb.tb_lineno
            frames.append(item)
            tb = tb.tb_next
        record = {
            "event": "worker_exception_before_generic_handler",
            "exception_type": exc_type.__name__,
            "exception_module": exc_type.__module__,
            "worker_location": location(frame), "traceback_locations": frames,
            "exception_text_retained": False, "locals_retained": False,
            "challenge_values_retained": False,
        }
        for attr in ("errno", "winerror"):
            value = getattr(exc, attr, None)
            if type(value) is int:
                record[attr] = value
        sys.stderr.write(json.dumps(record, sort_keys=True) + "\n")
        sys.stderr.flush()
    return trace

sys.stderr.write('{"event":"diagnostic_worker_started","source_modified":false}\n')
sys.stderr.flush()
sys.settrace(trace)
try:
    code = worker.main()
finally:
    sys.settrace(None)
sys.stderr.write(json.dumps({"event":"diagnostic_worker_finished", "returncode":code}) + "\n")
sys.stderr.flush()
raise SystemExit(code)
