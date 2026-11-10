#!/usr/bin/env python3
"""Préparer les copies des modules ; aucune installation système dans cet outil."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1] / "dotfiles"


def render_files(keyboard="us", variant="", root=ROOT):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", keyboard):
        raise ValueError("Disposition XKB invalide")
    if not re.fullmatch(r"[a-zA-Z0-9_-]*", variant):
        raise ValueError("Variante XKB invalide")
    if not root.is_dir():
        raise ValueError("Dossier dotfiles absent")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("Lien symbolique interdit dans les sources")
    def render(path):
        text = path.read_text(encoding="utf-8")
        text = text.replace("@KEYBOARD@", keyboard).replace("@VARIANT@", variant)
        if re.search(r"@[A-Z_]+@", text):
            raise ValueError("Paramètre non résolu dans " + str(path))
        return text
    files = {"user/" + path.relative_to(root / "user").as_posix(): render(path)
             for path in sorted((root / "user").rglob("*")) if path.is_file()}
    files["system/greetd.toml"] = render(root / "system/greetd/config.toml")
    # Greeter ne propose pas d'include documenté : assemblage ordonné des modules.
    modules = sorted((root / "system/noctalia-greeter").glob("*.toml"))
    if not modules:
        raise ValueError("Modules Greeter absents")
    files["system/greeter.toml"] = "\n".join(
        "# Module : " + path.name + "\n" + render(path) for path in modules)
    for required in ("user/umbriel/config.toml", "user/noctalia/config.toml", "user/kitty/kitty.conf"):
        if required not in files:
            raise ValueError("Point d'entrée absent : " + required)
    return files


def check_files(files, toml_parser=None):
    # Disponible nativement avec le paquet python actuel de CachyOS/Arch.
    if toml_parser is None:
        try:
            import tomllib as toml_parser
        except ImportError as error:
            raise ValueError("Validation TOML : Python >= 3.11 requis") from error
    parsed = {}
    for name, text in files.items():
        if name.endswith(".toml"):
            try:
                parsed[name] = toml_parser.loads(text)
            except ValueError as error:
                raise ValueError(name + " : " + str(error)) from error
    def includes(name, stack=()):
        if name in stack:
            raise ValueError("Cycle d'inclusions : " + name)
        data = parsed[name]
        result = [(name, data)]
        for child in data.get("include", {}).get("files", []):
            if child.startswith(("/", "~")) or ".." in Path(child).parts:
                raise ValueError("Include hors du profil : " + child)
            target = (Path(name).parent / child).as_posix()
            if target not in parsed:
                raise ValueError("Include absent : " + target)
            result.extend(includes(target, stack + (name,)))
        return result
    seen = set()
    for name, data in includes("user/umbriel/config.toml"):
        for key in data.get("keybinds", {}):
            if key in seen:
                raise ValueError("Raccourci défini plusieurs fois : " + key)
            seen.add(key)
    includes("user/noctalia/config.toml")
    for line in files["user/kitty/kitty.conf"].splitlines():
        if line.startswith("include "):
            target = "user/kitty/" + line.split(" ", 1)[1]
            if target not in files:
                raise ValueError("Include Kitty absent : " + target)


def write_files(files, destination):
    destination = Path(destination)
    # L'outil refuse tout dossier existant, même vide, et ne suit aucun lien.
    destination.mkdir(mode=0o700)
    for name, text in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("x", encoding="utf-8") as output:
            output.write(text)


def check_native_profiles(config_home, logs, runner=subprocess.run):
    """Contrôler les schémas des binaires installés, sans démarrer de bureau."""
    config_home = Path(config_home).resolve()
    logs = Path(logs)
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    commands = (
        ("noctalia", ["/usr/bin/noctalia", "config", "validate", str(config_home / "noctalia")]),
        ("umbriel", ["/usr/bin/umbriel", "config", "validate", "--json"]),
    )
    for name, command in commands:
        env = dict(os.environ, XDG_CONFIG_HOME=str(config_home), LC_ALL="C", NO_COLOR="1")
        result = runner(command, env=env, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        (logs / (name + ".log")).write_text(output, encoding="utf-8")
        if result.returncode:
            raise ValueError("Validation native échouée : " + name + " ; voir " + str(logs / (name + ".log")))
        if name == "umbriel":
            report = json.loads(result.stdout)
            if report.get("valid") is not True or report.get("diagnostics"):
                raise ValueError("Diagnostic Umbriel à corriger ; voir " + str(logs / "umbriel.log"))
        else:
            plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
            if re.search(r"(?im)^\s*WARN(?:ING)?\b", plain):
                raise ValueError("Avertissement Noctalia à corriger ; voir " + str(logs / "noctalia.log"))


def check_pam_session(pam_root):
    """Vérifier pam_systemd via les inclusions session ; ne modifier aucun PAM."""
    pam_root = Path(pam_root)
    def contains_runtime(service, visited=()):
        if service in visited or not re.fullmatch(r"[a-zA-Z0-9_.-]+", service):
            return False
        path = pam_root / service
        if not path.is_file():
            return False
        for raw in path.read_text().splitlines():
            fields = raw.split("#", 1)[0].split()
            if len(fields) >= 2 and fields[0] == "@include":
                if contains_runtime(fields[1], visited + (service,)):
                    return True
            if len(fields) < 3 or fields[0].lstrip("-") != "session":
                continue
            if fields[1] in ("include", "substack"):
                if contains_runtime(fields[2], visited + (service,)):
                    return True
            elif any(Path(word).name == "pam_systemd.so" for word in fields[2:]):
                return True
        return False
    if not contains_runtime("greetd"):
        raise ValueError("La pile PAM de greetd ne référence pas pam_systemd.so via ses sessions ; aucun PAM n'a été modifié")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyboard", default="us")
    parser.add_argument("--variant", default="")
    parser.add_argument("--check", action="store_true", help="Vérifier TOML, inclusions et raccourcis")
    parser.add_argument("--output", type=Path, help="Écrire dans un nouveau dossier de préparation")
    parser.add_argument("--print", action="store_true", dest="print_files", help="Afficher chaque fichier séparément")
    parser.add_argument("--check-native", type=Path, help="Valider un dossier XDG avec les binaires installés")
    parser.add_argument("--logs", type=Path, help="Dossier des journaux de validation native")
    parser.add_argument("--check-pam-root", type=Path, help="Vérifier les inclusions PAM de greetd sans modification")
    args = parser.parse_args()
    try:
        if args.check_native:
            if not args.logs:
                raise ValueError("--logs est requis avec --check-native")
            check_native_profiles(args.check_native, args.logs)
            print("Schémas Noctalia et Umbriel validés sans diagnostic")
            return
        if args.check_pam_root:
            check_pam_session(args.check_pam_root)
            print("Session PAM greetd reliée à systemd")
            return
        files = render_files(args.keyboard, args.variant)
        if args.check:
            check_files(files)
        if args.output:
            write_files(files, args.output)
        if args.print_files:
            for name, text in files.items():
                print("\n### " + name + "\n" + text, end="")
        if not (args.output or args.print_files):
            print(str(len(files)) + " fichiers préparés" + (" et vérifiés" if args.check else ""))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, "Erreur : " + str(error) + "\n")


if __name__ == "__main__":
    main()
