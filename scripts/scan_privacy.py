#!/usr/bin/env python3
"""
OTTO - Privacy Scanner
Named in honor of Otto - Protecting data like family

Supports:
- 🇧🇷 LGPD (Brazil - Lei 13.709/18)
- 🇪🇺 GDPR (Europe - EU 2016/679)

Usage:
  As Claude Code hook (receives JSON via stdin)
  Or standalone: python scan_privacy.py <file>
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


class PrivacyScanner:
    """Scans code for privacy violations based on LGPD or GDPR"""

    def __init__(self, regulation: str = 'lgpd'):
        """
        Initialize scanner with regulation type

        Args:
            regulation: 'lgpd', 'gdpr', or 'both'
        """
        self.regulation = regulation.lower()
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Any]:
        """Load regulation-specific patterns from JSON file"""
        script_dir = Path(__file__).parent
        patterns = {}

        if self.regulation in ['lgpd', 'both']:
            lgpd_file = script_dir / 'patterns.json'
            if lgpd_file.exists():
                with open(lgpd_file) as f:
                    lgpd_patterns = json.load(f)
                    patterns.update(lgpd_patterns)
            else:
                # Fallback: look for lgpd patterns in parent structure
                alt_path = script_dir.parent / 'skills' / 'lgpd' / 'patterns.json'
                if alt_path.exists():
                    with open(alt_path) as f:
                        patterns.update(json.load(f))

        if self.regulation in ['gdpr', 'both']:
            gdpr_file = script_dir.parent / 'skills' / 'gdpr' / 'patterns.json'
            if gdpr_file.exists():
                with open(gdpr_file) as f:
                    gdpr_patterns = json.load(f)
                    # Prefix GDPR patterns to avoid conflicts
                    patterns.update({f'gdpr_{k}': v for k, v in gdpr_patterns.items()})

        return patterns

    def scan(self, content: str, file_path: str = '') -> List[Dict[str, Any]]:
        """
        Scan content for privacy violations

        Args:
            content: Code content to scan
            file_path: Path to file being scanned

        Returns:
            List of violations found
        """
        violations = []

        for pattern_name, pattern_data in self.patterns.items():
            regex = pattern_data['regex']

            try:
                matches = list(re.finditer(regex, content, re.IGNORECASE | re.MULTILINE))

                if matches:
                    # Find line numbers for each match
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1

                        violations.append({
                            'type': pattern_name,
                            'severity': pattern_data['severity'],
                            'article': pattern_data['article'],
                            'message': pattern_data['message'],
                            'fix': pattern_data['fix'],
                            'fine': pattern_data.get('fine', 'Significant penalties'),
                            'line': line_num,
                            'matched_text': match.group(0)[:50]  # First 50 chars
                        })
            except re.error as e:
                # Skip invalid regex patterns
                print(f"Warning: Invalid regex for {pattern_name}: {e}", file=sys.stderr)
                continue

        # Sort by severity: critical > high > medium > low
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        violations.sort(key=lambda v: (severity_order.get(v['severity'], 999), v['line']))

        return violations

    def format_output(self, violations: List[Dict[str, Any]], file_path: str = '') -> str:
        """
        Format violations as Claude-friendly output

        Args:
            violations: List of violations from scan()
            file_path: Path to file being scanned

        Returns:
            Formatted output string
        """
        regulation_name = {
            'lgpd': 'LGPD',
            'gdpr': 'GDPR',
            'both': 'LGPD+GDPR'
        }.get(self.regulation, 'Privacy')

        if not violations:
            return f"""
🛡️ OTTO - {regulation_name} Analysis

✅ No violations detected.
   Code complies with {regulation_name} requirements.

🛡️ OTTO protected your users today.
"""

        critical_count = sum(1 for v in violations if v['severity'] == 'critical')
        high_count = sum(1 for v in violations if v['severity'] == 'high')
        medium_count = sum(1 for v in violations if v['severity'] == 'medium')

        output = f"""
🛡️ OTTO - {regulation_name} Privacy Analysis

❌ VIOLATIONS FOUND: {len(violations)}

📁 File: {file_path or 'stdin'}

"""

        for i, v in enumerate(violations, 1):
            emoji = "🚨" if v['severity'] == 'critical' else "⚠️" if v['severity'] == 'high' else "⚡"

            output += f"""{i}. {emoji} {v['type'].replace('_', ' ').title()}
   Line: {v['line']}
   Severity: {v['severity'].upper()}

   ⚠️  Issue:
   {v['message']}

   📋 Legal basis violated:
   {v['article']}

   💰 Fine risk:
   {v['fine']}

   🔧 SUGGESTED FIX:
   {v['fix']}

"""

        output += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY:
   • {critical_count} critical violations 🚨
   • {high_count} high severity violations ⚠️
   • {medium_count} medium severity violations ⚡

✅ NEXT STEPS:
1. Fix critical violations immediately
2. Implement consent verification system
3. Add privacy tests to CI/CD
4. Document legal basis for data processing

🛡️ OTTO protected your users today.
"""

        return output


def main():
    """Main entry point for hook or standalone usage"""

    # Determine regulation from file marker if exists
    regulation = 'lgpd'  # default

    # Check for .regulation file in skill directory
    home = Path.home()
    regulation_file = home / '.claude' / 'skills' / 'otto' / '.regulation'

    if regulation_file.exists():
        regulation = regulation_file.read_text().strip()

    scanner = PrivacyScanner(regulation)

    # Check if standalone mode (file argument provided)
    if len(sys.argv) >= 2:
        # Standalone mode: scan file from command line
        file_path = sys.argv[1]

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

        violations = scanner.scan(content, file_path)
        print(scanner.format_output(violations, file_path))

        # Exit with code 1 if violations found
        sys.exit(1 if violations else 0)

    # Hook mode: read JSON from stdin
    elif not sys.stdin.isatty():
        # Hook mode: read JSON from stdin
        try:
            data = json.load(sys.stdin)
            tool_input = data.get('tool_input', {})

            # Extract content from different tool types
            content = (
                tool_input.get('new_string') or
                tool_input.get('content') or
                tool_input.get('code') or
                ''
            )

            file_path = tool_input.get('file_path', '')

            if not content:
                # No content to scan
                sys.exit(0)

            violations = scanner.scan(content, file_path)

            if violations:
                # Output to stderr so Claude sees it
                print(scanner.format_output(violations, file_path), file=sys.stderr)

                # Return JSON feedback for Claude Code
                feedback = {
                    "blocked": True,
                    "feedback": scanner.format_output(violations, file_path)
                }
                print(json.dumps(feedback))

                # Exit code 2 = block the operation
                sys.exit(2)

            # No violations - allow operation
            sys.exit(0)

        except json.JSONDecodeError:
            print("Error: Invalid JSON input", file=sys.stderr)
            sys.exit(1)

    else:
        # No input provided
        print("Usage: python scan_privacy.py <file>")
        print("Or pipe JSON from Claude Code hook")
        sys.exit(1)


if __name__ == '__main__':
    main()
