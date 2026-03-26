import argparse
from datetime import datetime, timezone

from deadcode_finder.analyzer import DeadCodeAnalyzer
from deadcode_finder.report import ReportGenerator
from deadcode_finder.server import RemovalServer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--output", "-o", default="deadcode_report.html")
    parser.add_argument("--port", "-p", type=int, default=8765, help="Port for removal server")
    parser.add_argument("--no-server", action="store_true", help="Don't start removal server")
    args = parser.parse_args()

    print("[*] Scanning:", args.path)
    analyzer = DeadCodeAnalyzer(args.path)
    analyzer.scan()

    # Start removal server
    server = None
    server_url = None
    if not args.no_server:
        server = RemovalServer(args.path, args.port)
        server_url = server.start()
        if server_url:
            print(f"[+] Removal server started at {server_url}")

    report = analyzer.get_report()
    counts = report.get("counts", {})

    def _count_grouped_items(grouped):
        if isinstance(grouped, dict):
            return sum(len(items) for items in grouped.values())
        if isinstance(grouped, list):
            return len(grouped)
        return 0

    high_counts = counts.get("high_confidence", {})
    potential_counts = counts.get("potentially_used", {})

    high_total = int(high_counts.get("total", 0))
    potential_total = int(potential_counts.get("total", 0))
    unreachable_total = int(counts.get("unreachable", 0))

    if not counts:
        high_total = (
            _count_grouped_items(report.get("unused_imports", {}))
            + len(report.get("unused_functions", []))
            + len(report.get("unused_classes", []))
            + _count_grouped_items(report.get("unused_variables", {}))
        )
        potential_total = 0
        unreachable_total = _count_grouped_items(report.get("unreachable_code", {}))

    total_issues = int(counts.get("total_findings", high_total + potential_total + unreachable_total))

    # Conservative scoring:
    # high-confidence findings count fully; potentially-used findings are weighted lower.
    weighted_issues = high_total + int(round(potential_total * 0.35)) + unreachable_total

    if weighted_issues == 0:
        health = 100
    elif weighted_issues <= 5:
        health = 96
    elif weighted_issues <= 15:
        health = 88
    elif weighted_issues <= 30:
        health = 75
    elif weighted_issues <= 60:
        health = 58
    elif weighted_issues <= 100:
        health = 40
    else:
        health = max(5, 100 - weighted_issues)

    # Color logic
    if health >= 80:
        color = "#51cf66"  # green
    elif health >= 50:
        color = "#ffd93d"  # yellow
    else:
        color = "#ff6b6b"  # red

    report["health"] = health
    report["health_color"] = color
    report["total_issues"] = total_issues
    report["high_confidence_total"] = high_total
    report["potentially_used_total"] = potential_total
    report["unreachable_total"] = unreachable_total
    report["generated_at"] = datetime.now(timezone.utc).astimezone().strftime("%b %d, %Y %H:%M %Z")
    report["server_url"] = server_url if server_url else ""

    generator = ReportGenerator()
    generator.generate(args.output, report)
    
    if server and server.is_running():
        print("[+] Server is running. Keep this terminal open to use removal features.")
        print("[!] Press Ctrl+C to stop the server and exit.")
        try:
            # Keep the main thread alive while server runs
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Shutting down server...")
            server.stop()
            print("[+] Server stopped.")

if __name__ == "__main__":
    main()
