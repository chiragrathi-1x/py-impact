import argparse
import sys
import logging
from pathlib import Path
from .analyzer import Analyzer
from .formatter import format_tree, export_dot, export_json

def main():
    parser = argparse.ArgumentParser(
        prog="py-impact",
        description="Static analysis tool to map internal call graphs."
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Analyze command
    analyze_p = subparsers.add_parser("analyze", help="Analyze impact of a specific target")
    analyze_p.add_argument("path", type=str, help="Project root directory")
    analyze_p.add_argument("--target", type=str, required=True, 
                          help="Target symbol (fqn) or file:line (e.g. utils.py:42)")
    analyze_p.add_argument("--exclude", type=str, nargs="*", help="Paths to exclude")

    # Orphans command
    orphans_p = subparsers.add_parser("orphans", help="Find unused functions/classes")
    orphans_p.add_argument("path", type=str, help="Project root directory")
    orphans_p.add_argument("--exclude", type=str, nargs="*", help="Paths to exclude")

    # Hotspots command
    hotspots_p = subparsers.add_parser("hotspots", help="Find most depended-upon symbols")
    hotspots_p.add_argument("path", type=str, help="Project root directory")
    hotspots_p.add_argument("--limit", type=int, default=10, help="Number of results")
    hotspots_p.add_argument("--exclude", type=str, nargs="*", help="Paths to exclude")

    # Graph command
    graph_p = subparsers.add_parser("graph", help="Export call graph")
    graph_p.add_argument("path", type=str, help="Project root directory")
    graph_p.add_argument("--output", type=str, help="Output file path")
    graph_p.add_argument("--format", choices=["dot", "json"], default="dot", help="Export format")
    graph_p.add_argument("--exclude", type=str, nargs="*", help="Paths to exclude")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    root = Path(args.path)
    if not root.exists():
        print(f"Error: Path {root} does not exist.")
        sys.exit(1)

    analyzer = Analyzer(root, exclude_patterns=args.exclude)
    print(f"Analyzing project at {root}...")
    analyzer.run()

    if args.command == "analyze":
        target = args.target
        target_fqn = None
        
        if ":" in target:
            file_part, line_part = target.split(":")
            target_file = Path(file_part)
            try:
                line_no = int(line_part)
                sym = analyzer.graph.find_symbol_at_line(target_file, line_no)
                if sym:
                    target_fqn = sym.fqn
                else:
                    print(f"Could not find a symbol at {file_part}:{line_part}")
                    sys.exit(1)
            except ValueError:
                print(f"Invalid line number: {line_part}")
                sys.exit(1)
        else:
            target_fqn = target

        if target_fqn not in analyzer.graph.symbols:
            print(f"Symbol '{target_fqn}' not found in project index.")
            sys.exit(1)

        print(f"\nBlast Radius for {target_fqn}:")
        print("=" * 40)
        print(format_tree(analyzer.graph, target_fqn))

    elif args.command == "orphans":
        orphans = analyzer.get_orphans()
        print(f"\nFound {len(orphans)} orphans:")
        for o in sorted(orphans, key=lambda x: x.fqn):
            print(f"- {o.fqn} ({o.file_path}:{o.line_start})")

    elif args.command == "hotspots":
        hotspots = analyzer.get_hotspots(args.limit)
        print(f"\nTop {len(hotspots)} Hotspots (by incoming calls):")
        for fqn, count in hotspots:
            print(f"{count:4} <- {fqn}")

    elif args.command == "graph":
        output_content = ""
        if args.format == "dot":
            output_content = export_dot(analyzer.graph)
        else:
            output_content = export_json(analyzer.graph)
        
        if args.output:
            Path(args.output).write_text(output_content, encoding="utf-8")
            print(f"Graph exported to {args.output}")
        else:
            print(output_content)

if __name__ == "__main__":
    main()
