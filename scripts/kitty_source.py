#!/usr/bin/env python3
"""Lire Kitty depuis CachyOS/main et préparer des fichiers ; aucun déploiement."""
from datetime import datetime, timezone
import hashlib
import io
import json
import posixpath
from pathlib import PurePosixPath
import re
import shlex
import stat
from urllib.request import Request, urlopen
import zipfile

REPOSITORY = "Masternaka/CachyOS"
BRANCH = "main"
SOURCE = "Dotfiles/kitty/.config/kitty"
MAX_DOWNLOAD = 32 * 1024 * 1024
MAX_FILES = 100
MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_TOTAL_SIZE = 8 * 1024 * 1024


def download(url):
    request = Request(url, headers={"User-Agent": "Cachy-setup", "Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=30) as response:
        if not response.url.startswith("https://"):
            raise ValueError("Redirection non HTTPS refusée")
        data = response.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise ValueError("Téléchargement GitHub trop volumineux")
    return data


def check_kitty_files(files):
    """Valider les inclusions statiques dans le profil préparé, sans exécuter Kitty."""
    if "kitty.conf" not in files:
        raise ValueError("Point d'entrée Kitty absent")
    graph = {}
    def children_for(name):
        children = []
        for line in files[name].splitlines():
            tokens = shlex.split(line, comments=True) if re.match(r"\s*(?:include|globinclude|envinclude|geninclude)\b", line) else []
            if not tokens:
                continue
            if tokens[0] != "include" or len(tokens) != 2:
                raise ValueError("Inclusion Kitty non statique ou ambiguë : " + name)
            target = tokens[1]
            if target.startswith(("/", "~")) or "$" in target or "\\" in target:
                raise ValueError("Include Kitty hors du profil : " + target)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
            if target == ".." or target.startswith("../") or target not in files:
                raise ValueError("Include Kitty absent ou hors du profil : " + target)
            children.append(target)
        return children
    def visit(name, stack=()):
        if name in stack:
            raise ValueError("Cycle d'inclusions Kitty : " + name)
        if name not in graph:
            graph[name] = children_for(name)
        for child in graph[name]:
            visit(child, stack + (name,))
    for name in files:
        if name.endswith(".conf"):
            visit(name)


def prepare_kitty_files(original):
    """Rendre les anciennes inclusions ~/.config/kitty relatives, pour tout XDG."""
    prepared = dict(original)
    adaptations = []
    for name, content in original.items():
        if not name.endswith(".conf"):
            continue
        lines = []
        for line in content.splitlines(keepends=True):
            if re.match(r"\s*include\s+", line):
                tokens = shlex.split(line, comments=True)
                if len(tokens) == 2 and tokens[1].startswith("~/.config/kitty/"):
                    target = tokens[1][len("~/.config/kitty/"):]
                    if ".." in PurePosixPath(target).parts or target not in original:
                        raise ValueError("Include Kitty absent ou hors du profil : " + target)
                    relative = posixpath.relpath(target, posixpath.dirname(name) or ".")
                    # Ne modifier que le chemin, conserver commentaires et options.
                    line = line.replace(tokens[1], relative, 1)
                    adaptations.append({"file": name, "from": tokens[1], "to": relative})
            lines.append(line)
        prepared[name] = "".join(lines)
    check_kitty_files(prepared)
    return prepared, adaptations


def fetch_kitty(fetch=download):
    """Résoudre main une seule fois ; télécharger tous les fichiers de ce commit."""
    metadata = json.loads(fetch("https://api.github.com/repos/" + REPOSITORY + "/commits/" + BRANCH))
    commit = metadata.get("sha", "") if isinstance(metadata, dict) else ""
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Commit GitHub illisible : récupération Kitty refusée")
    archive_url = "https://codeload.github.com/" + REPOSITORY + "/zip/" + commit
    data = fetch(archive_url)
    if len(data) > MAX_DOWNLOAD:
        raise ValueError("Archive GitHub trop volumineuse")
    prefix = "CachyOS-" + commit + "/" + SOURCE + "/"
    original = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if not member.filename.startswith(prefix):
                    continue
                name = member.filename[len(prefix):]
                if not name and member.is_dir():
                    continue
                parts = PurePosixPath(name).parts
                if not name or name.startswith("/") or ".." in parts or "\\" in name or any(ord(c) < 32 for c in name):
                    raise ValueError("Chemin Kitty non valide dans l'archive")
                mode = member.external_attr >> 16
                if member.is_dir():
                    if stat.S_IFMT(mode) not in (0, stat.S_IFDIR):
                        raise ValueError("Répertoire Kitty redirigé")
                    continue
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise ValueError("Lien ou fichier spécial Kitty refusé : " + name)
                if posixpath.normpath(name) != name or name in original:
                    raise ValueError("Chemin Kitty ambigu ou en double : " + name)
                total += member.file_size
                if len(original) >= MAX_FILES or member.file_size > MAX_FILE_SIZE or total > MAX_TOTAL_SIZE:
                    raise ValueError("Profil Kitty trop volumineux")
                original[name] = archive.read(member).decode("utf-8")
    except zipfile.BadZipFile as error:
        raise ValueError("Archive Kitty invalide ou corrompue") from error
    prepared, adaptations = prepare_kitty_files(original)
    provenance = {
        "repository": REPOSITORY, "branch": BRANCH, "commit": commit,
        "source": SOURCE, "archive_url": archive_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "adapted_includes": adaptations,
        "files": {name: {
            "original_sha256": hashlib.sha256(original[name].encode("utf-8")).hexdigest(),
            "prepared_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        } for name, content in prepared.items()},
    }
    return prepared, provenance
