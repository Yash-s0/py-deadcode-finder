import argparse
from deadcode_finder.analyzer import DeadCodeAnalyzer
from deadcode_finder.report import ReportGenerator
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--output", "-o", default="deadcode_report.html")
    args = parser.parse_args()

    print("[*] Scanning:", args.path)
    analyzer = DeadCodeAnalyzer(args.path)
    analyzer.scan()

    report = analyzer.get_report()
    report["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    generator = ReportGenerator()
    generator.generate(args.output, report)

if __name__ == "__main__":
    main()
