#!/usr/bin/env python3
"""Vérifier les liens Markdown locaux et leurs ancres, sans réseau ni écriture."""
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def prose(text):
    result = []
    fence = None
    for line in text.splitlines():
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            marker = match[1][0]
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is None:
            result.append(line)
    return result


def anchors(text):
    result = set()
    counts = {}
    for line in prose(text):
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if not match:
            continue
        title = match[1].lower()
        title = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', title)
        slug = ''.join(c for c in title if c in '-_ ' or unicodedata.category(c)[0] in 'LN').replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug + ('-' + str(count) if count else ''))
    return result


def check(root=ROOT):
    errors = []
    total = 0
    files = [root / 'README.md', root / 'AGENTS.md', *sorted((root / 'docs').glob('*.md'))]
    for path in files:
        if not path.is_file():
            errors.append('Document absent : ' + str(path))
            continue
        for match in re.finditer(r'\[[^\]\n]+\]\((<[^>]+>|[^)\s]+)\)', '\n'.join(prose(path.read_text()))):
            target = match[1].strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            total += 1
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if destination != root.resolve() and root.resolve() not in destination.parents:
                errors.append(str(path.relative_to(root)) + ' : lien hors dépôt ' + target)
            elif not destination.exists():
                errors.append(str(path.relative_to(root)) + ' : chemin absent ' + target)
            elif parsed.fragment and destination.suffix == '.md' and destination.is_file():
                if unquote(parsed.fragment) not in anchors(destination.read_text()):
                    errors.append(str(path.relative_to(root)) + ' : ancre absente ' + target)
    return total, errors


def main():
    total, errors = check()
    print(str(total) + ' liens locaux contrôlés ; ' + str(len(errors)) + ' erreur(s).')
    for error in errors:
        print(error, file=sys.stderr)
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
