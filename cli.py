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
