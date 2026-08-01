"""Check per-module coverage thresholds from coverage.json."""
import json
import sys

THRESHOLDS = {
    "calendar_planner/app/mcp_transport.py": 0.80,
    "calendar_planner/calendar/mcp_gateway.py": 0.80,
    "calendar_planner/calendar/creator.py": 0.90,
}


def main() -> int:
    try:
        with open("coverage.json") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("ERROR: coverage.json not found. Run pytest with --cov-report=json:coverage.json")
        return 1
    except json.JSONDecodeError:
        print("ERROR: coverage.json is invalid JSON")
        return 1

    files_data = data.get("files", {})

    ok = True
    for mod_path, threshold in sorted(THRESHOLDS.items()):
        found = False
        for file_key, file_info in files_data.items():
            norm_key = file_key.replace("\\", "/")
            if norm_key.endswith(mod_path) or mod_path in norm_key:
                summary = file_info.get("summary", {})
                pct_lines = float(summary.get("percent_covered", 0))
                actual = pct_lines / 100.0
                found = True

                if actual >= threshold:
                    print(f"PASS: {mod_path} = {actual:.0%} (threshold {threshold:.0%})")
                else:
                    print(f"FAIL: {mod_path} = {actual:.0%} (threshold {threshold:.0%})")
                    ok = False
                break

        if not found:
            for file_key, file_info in files_data.items():
                norm_key = file_key.replace("\\", "/")
                if mod_path.split("/")[-1] in norm_key.split("/")[-1]:
                    summary = file_info.get("summary", {})
                    pct_lines = float(summary.get("percent_covered", 0))
                    actual = pct_lines / 100.0
                    found = True

                    if actual >= threshold:
                        print(f"PASS: {mod_path} = {actual:.0%} (threshold {threshold:.0%})")
                    else:
                        print(f"FAIL: {mod_path} = {actual:.0%} (threshold {threshold:.0%})")
                        ok = False
                    break

        if not found:
            print(f"WARN: {mod_path} not found in coverage data")
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())