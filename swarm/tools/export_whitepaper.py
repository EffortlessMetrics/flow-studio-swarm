#!/usr/bin/env python3
"""Export whitepaper to PDF/HTML/DOCX using pandoc."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WHITEPAPER_PATH = REPO_ROOT / "docs" / "WHITEPAPER.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "whitepaper"

REQUIRED_SECTIONS = [
    "Executive Summary",
    "The Problem",
    "Core Philosophy",
    "Architecture",
    "How It Works",
    "Operational Proof",
    "Adoption Path",
    "Differentiation",
]

FORMAT_EXTENSIONS = {
    "pdf": ".pdf",
    "html": ".html",
    "docx": ".docx",
}


def check_pandoc_installed() -> bool:
    """Check if pandoc is available in PATH."""
    return shutil.which("pandoc") is not None


def check_sections(content: str) -> list[str]:
    """Check whitepaper has required sections. Return missing ones."""
    missing = []
    for section in REQUIRED_SECTIONS:
        # Look for section as markdown header (## or #)
        # Section could be numbered like "## 1. The Problem" or plain "## The Problem"
        patterns = [
            f"# {section}",
            f"## {section}",
            f"### {section}",
            # Also check for numbered sections like "## 1. The Problem"
            f". {section}",
        ]
        found = any(pattern in content for pattern in patterns)
        if not found:
            missing.append(section)
    return missing


def export_whitepaper(output_path: Path, format: str) -> int:
    """Export whitepaper using pandoc. Return exit code."""
    if not WHITEPAPER_PATH.exists():
        print(f"Error: Whitepaper not found at {WHITEPAPER_PATH}", file=sys.stderr)
        return 1

    if not check_pandoc_installed():
        print(
            "Error: pandoc is not installed or not in PATH.\n"
            "Install pandoc from https://pandoc.org/installing.html\n"
            "  - macOS: brew install pandoc\n"
            "  - Ubuntu/Debian: sudo apt-get install pandoc\n"
            "  - Windows: choco install pandoc",
            file=sys.stderr,
        )
        return 1

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build pandoc command
    cmd = [
        "pandoc",
        str(WHITEPAPER_PATH),
        "-o",
        str(output_path),
        "--standalone",
    ]

    # Add format-specific options
    if format == "pdf":
        # Use default PDF engine (pdflatex, or xelatex if available)
        cmd.extend(["--pdf-engine=xelatex"])
    elif format == "html":
        cmd.extend(["--self-contained", "--metadata", "title=Self-Governing CI Whitepaper"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: pandoc failed with exit code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            # Check for common PDF engine issues
            if format == "pdf" and "xelatex" in result.stderr:
                print(
                    "\nHint: xelatex not found. Install texlive or try:\n"
                    "  pandoc ... --pdf-engine=pdflatex\n"
                    "  pandoc ... --pdf-engine=wkhtmltopdf",
                    file=sys.stderr,
                )
            return 1

        print(f"Exported whitepaper to {output_path}")
        return 0

    except FileNotFoundError:
        print(
            "Error: pandoc command failed to execute.\nEnsure pandoc is properly installed.",
            file=sys.stderr,
        )
        return 1
    except subprocess.SubprocessError as e:
        print(f"Error: subprocess error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export whitepaper to PDF/HTML/DOCX using pandoc.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Export to PDF (default)
  %(prog)s --format html            # Export to HTML
  %(prog)s --output /tmp/wp.pdf     # Custom output path
  %(prog)s --check                  # Verify required sections exist
        """,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: artifacts/whitepaper/WHITEPAPER.<format>)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["pdf", "html", "docx"],
        default="pdf",
        help="Output format (default: pdf)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify whitepaper has required sections (does not export)",
    )

    args = parser.parse_args()

    # Check mode: verify sections only
    if args.check:
        if not WHITEPAPER_PATH.exists():
            print(f"Error: Whitepaper not found at {WHITEPAPER_PATH}", file=sys.stderr)
            return 1

        content = WHITEPAPER_PATH.read_text()
        missing = check_sections(content)

        if missing:
            print("Missing required sections:", file=sys.stderr)
            for section in missing:
                print(f"  - {section}", file=sys.stderr)
            return 1

        print(f"All {len(REQUIRED_SECTIONS)} required sections present.")
        return 0

    # Export mode
    if args.output:
        output_path = args.output
    else:
        extension = FORMAT_EXTENSIONS[args.format]
        output_path = DEFAULT_OUTPUT_DIR / f"WHITEPAPER{extension}"

    return export_whitepaper(output_path, args.format)


if __name__ == "__main__":
    sys.exit(main())
