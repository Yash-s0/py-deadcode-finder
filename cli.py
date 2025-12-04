import argparse
from datetime import datetime, timezone

from deadcode_finder.analyzer import DeadCodeAnalyzer
from deadcode_finder.report import ReportGenerator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--output", "-o", default="deadcode_report.html")
    args = parser.parse_args()

    print("[*] Scanning:", args.path)
    analyzer = DeadCodeAnalyzer(args.path)
    analyzer.scan()

    report = analyzer.get_report()
    # === IMPROVED SCORING (much more realistic) ===
    total_issues = sum([
        len(report.get("unused_imports", [])),
        len(report.get("unused_functions", [])),
        len(report.get("unused_classes", [])),
        len(report.get("unused_variables", [])),
        len(report.get("unreachable_code", [])),
    ])

    # New scoring: less punishing, more graduated
    if total_issues == 0:
        health = 100
    elif total_issues <= 5:
        health = 95
    elif total_issues <= 15:
        health = 85
    elif total_issues <= 30:
        health = 70
    elif total_issues <= 60:
        health = 50
    elif total_issues <= 100:
        health = 30
    else:
        health = max(5, 100 - total_issues)  # never go full 0, keep at least 5%

    health = int(health)

    # Color logic (same as before but slightly adjusted thresholds)
    if health >= 80:
        color = "#51cf66"  # green
    elif health >= 50:
        color = "#ffd93d"  # yellow
    else:
        color = "#ff6b6b"  # red
    # ================================================

    report["health"] = health
    report["health_color"] = color
    report["total_issues"] = total_issues
    report["generated_at"] = datetime.now(timezone.utc).astimezone().strftime("%b %d, %Y %H:%M %Z")

    generator = ReportGenerator()
    generator.generate(args.output, report)

if __name__ == "__main__":
    main()
