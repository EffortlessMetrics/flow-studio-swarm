#!/usr/bin/env python3
"""Analyze Python files for size metrics and modularization candidates."""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class FileAnalyzer(ast.NodeVisitor):
    """AST visitor to count functions, classes, and cyclomatic complexity."""

    def __init__(self):
        self.function_count = 0
        self.class_count = 0
        self.cyclomatic_complexity = 0

    def visit_FunctionDef(self, node):
        self.function_count += 1
        # Count control flow statements within the function
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                self.cyclomatic_complexity += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.function_count += 1
        # Count control flow statements within the function
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                self.cyclomatic_complexity += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.class_count += 1
        self.generic_visit(node)


def analyze_file(filepath: Path) -> Dict[str, int]:
    """Analyze a Python file and return metrics."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    # Count lines
    line_count = len(content.splitlines())

    # Parse AST
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # File has syntax errors, return basic metrics
        return {
            'line_count': line_count,
            'function_count': 0,
            'class_count': 0,
            'cyclomatic_complexity': 0,
        }

    analyzer = FileAnalyzer()
    analyzer.visit(tree)

    return {
        'line_count': line_count,
        'function_count': analyzer.function_count,
        'class_count': analyzer.class_count,
        'cyclomatic_complexity': analyzer.cyclomatic_complexity,
    }


def find_python_files(directories: List[Path]) -> List[Path]:
    """Find all Python files in the given directories."""
    python_files = []
    for directory in directories:
        if directory.exists():
            for filepath in directory.rglob('*.py'):
                python_files.append(filepath)
    return python_files


def main():
    """Main analysis function."""
    base_dir = Path('c:/Code/Swarm/flow-studio-swarm')
    directories = [
        base_dir / 'swarm',
        base_dir / 'src',
        base_dir / 'tests',
    ]

    print("Finding Python files...")
    python_files = find_python_files(directories)
    print(f"Found {len(python_files)} Python files\n")

    results = []

    for filepath in python_files:
        rel_path = str(filepath.relative_to(base_dir))
        metrics = analyze_file(filepath)
        if metrics:
            results.append({
                'path': rel_path,
                **metrics,
            })

    # Sort by line count descending
    results.sort(key=lambda x: x['line_count'], reverse=True)

    # Print top 10 by line count
    print("=" * 80)
    print("TOP 10 FILES BY LINE COUNT")
    print("=" * 80)
    print(f"{'Path':<50} {'LOC':>6} {'Funcs':>6} {'Classes':>6} {'CC':>6}")
    print("-" * 80)
    for i, r in enumerate(results[:10], 1):
        print(f"{i}. {r['path']:<48} {r['line_count']:>6} {r['function_count']:>6} {r['class_count']:>6} {r['cyclomatic_complexity']:>6}")

    # Identify modularization candidates
    print("\n" + "=" * 80)
    print("MODULARIZATION CANDIDATES")
    print("=" * 80)
    candidates = []
    for r in results:
        reasons = []
        if r['line_count'] > 500:
            reasons.append(f"LOC={r['line_count']}")
        if r['function_count'] > 20:
            reasons.append(f"Funcs={r['function_count']}")
        if r['class_count'] > 5:
            reasons.append(f"Classes={r['class_count']}")

        if reasons:
            candidates.append({
                'path': r['path'],
                'line_count': r['line_count'],
                'function_count': r['function_count'],
                'class_count': r['class_count'],
                'cyclomatic_complexity': r['cyclomatic_complexity'],
                'reasons': ', '.join(reasons),
            })

    print(f"\nFound {len(candidates)} candidates for modularization:\n")
    print(f"{'Path':<50} {'LOC':>6} {'Funcs':>6} {'Classes':>6} {'CC':>6} {'Reasons'}")
    print("-" * 100)
    for c in candidates:
        print(f"{c['path']:<48} {c['line_count']:>6} {c['function_count']:>6} {c['class_count']:>6} {c['cyclomatic_complexity']:>6} {c['reasons']}")

    # Print raw data in JSON format for further processing
    print("\n" + "=" * 80)
    print("RAW DATA (JSON format)")
    print("=" * 80)
    import json
    print(json.dumps(results, indent=2))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Python files analyzed: {len(results)}")
    print(f"Total lines of code: {sum(r['line_count'] for r in results)}")
    print(f"Total functions: {sum(r['function_count'] for r in results)}")
    print(f"Total classes: {sum(r['class_count'] for r in results)}")
    print(f"Modularization candidates: {len(candidates)}")


if __name__ == '__main__':
    main()
