#!/usr/bin/env python3
"""Aperçu, mise à jour ciblée, diagnostic et restauration des profils utilisateur."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile

from kitty_source import check_kitty_files, fetch_kitty
from noctalia_dotfiles import check_files, check_native_profiles, render_files, validate_native_result

PROFILES = ('umbriel', 'noctalia', 'kitty')
LIMIT = 16 * 1024 * 1024


def safe_path(path):
    """Refuser les liens dans tous les parents, y compris les liens pendants."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path != Path(os.path.normpath(str(path))):
        raise ValueError('Chemin absolu normalisé requis : ' + str(path))
    for part in (*reversed(path.parents), path):
        if part.is_symlink():
            raise ValueError('Lien symbolique refusé : ' + str(part))
    return path


def locations():
    home = safe_path(Path.home())
    config = safe_path(Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))))
    state = safe_path(Path(os.environ.get('XDG_STATE_HOME', str(home / '.local/state'))))
    if home not in config.parents or home not in state.parents or config == state or config in state.parents or state in config.parents:
        raise ValueError('Dossiers XDG distincts, sans imbrication et sous HOME requis')
    for variable, expected in (('NOCTALIA_CONFIG_HOME', config), ('NOCTALIA_STATE_HOME', state)):
        if os.environ.get(variable, str(expected)) != str(expected):
            raise ValueError(variable + ' redirige le profil ; examiner ce réglage')
    return config, state


def snapshot(path):
    """Empreinte des contenus, types et modes ; aucune lecture de liens ou FIFO."""
    path = safe_path(path)
    if not path.exists():
        return None
    entries = [path]
    result = {}
    size = 0
    while entries:
        if len(result) > 10000:
            raise ValueError('Profil contenant trop d’entrées')
        entry = entries.pop()
        info = entry.lstat()
        name = '.' if entry == path else entry.relative_to(path).as_posix()
        if any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise ValueError('Nom de fichier contenant un caractère de contrôle')
        if info.st_uid != os.getuid():
            raise ValueError('Fichier appartenant à un autre utilisateur : ' + str(entry))
        if stat.S_ISDIR(info.st_mode):
            result[name] = {'type': 'dir', 'mode': stat.S_IMODE(info.st_mode)}
            entries.extend(entry.iterdir())
        elif stat.S_ISREG(info.st_mode):
            size += info.st_size
            if size > LIMIT or len(result) > 10000:
                raise ValueError('Profil trop volumineux pour cet outil')
            result[name] = {'type': 'file', 'mode': stat.S_IMODE(info.st_mode),
                            'sha256': hashlib.sha256(entry.read_bytes()).hexdigest()}
        else:
            raise ValueError('Lien ou fichier spécial refusé : ' + str(entry))
    return result


def text_safe(text):
    return ''.join(c if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127) else '\\x%02x' % ord(c) for c in text)


def show_diff(current, proposed, output=print):
    """Le plan affiche aussi les suppressions ; les contenus binaires restent masqués."""
    before, after = snapshot(current) or {}, snapshot(proposed) or {}
    changes = 0
    for name in sorted(set(before) | set(after)):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        changes += 1
        output(('AJOUT ' if old is None else 'SUPPRESSION ' if new is None else 'MODIFICATION ') + name)
        if (old and old['type'] != 'file') or (new and new['type'] != 'file'):
            continue
        try:
            left = (current if name == '.' else current / name).read_text() if old else ''
            right = (proposed if name == '.' else proposed / name).read_text() if new else ''
            output(text_safe(''.join(difflib.unified_diff(left.splitlines(True), right.splitlines(True),
                                                       fromfile='actif/' + name, tofile='proposé/' + name))))
        except UnicodeDecodeError:
            output('Contenu binaire : seules les empreintes sont comparées.')
    if not changes:
        output('Aucune différence.')
    return changes


def check_target():
    if platform.system() != 'Linux' or not Path('/etc/os-release').is_file():
        raise ValueError('Application réservée à CachyOS installé')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID', '').strip('"\'') != 'cachyos' or Path('/run/archiso').exists() or os.geteuid() == 0:
        raise ValueError('CachyOS installé et utilisateur ordinaire requis, sans sudo')
    if not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_TTY'):
        raise ValueError('Terminal local interactif requis')


def prepare(profile, keyboard, variant, fetch=False):
    if profile == 'kitty':
        if not fetch:
            return None, None
        files, provenance = fetch_kitty()
        return files, provenance
    files = render_files(keyboard, variant)
    check_files(files)
    prefix = 'user/' + profile + '/'
    return {name[len(prefix):]: text for name, text in files.items() if name.startswith(prefix)}, None


def write_profile(files, path):
    path.mkdir(mode=0o700)
    for name, content in files.items():
        target = path / name
        if name.startswith('/') or '..' in Path(name).parts:
            raise ValueError('Chemin hors du profil')
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_text(content, encoding='utf-8')
        target.chmod(0o600)


def validate(profile, config, logs):
    if profile == 'kitty':
        files = {p.relative_to(config / profile).as_posix(): p.read_text(encoding='utf-8')
                 for p in (config / profile).rglob('*') if p.is_file()}
        check_kitty_files(files)
        return
    check_native_profiles(config, logs, profiles=(profile,))


def private_dir(path):
    safe_path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir() or path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError('Dossier privé appartenant au compte requis : ' + str(path))


@contextmanager
def operation_lock(state):
    import fcntl
    folder = state / 'cachy-setup'
    private_dir(folder)
    lock = safe_path(folder / 'profiles.lock')
    fd = os.open(str(lock), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError('Verrou non sûr')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Une autre opération sur les profils est en cours') from error
        yield
    finally:
        os.close(fd)


def save_json(path, value):
    # Les journaux et manifestes ne sont jamais exécutés lors d'une restauration.
    temporary = path.with_suffix('.new')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    temporary.chmod(0o600)
    os.replace(temporary, path)


def transact(profile, config, state, proposed, before, settings_before, reset_gui=False,
             provenance=None, validator=validate):
    """Sauvegarder, valider, recontrôler puis remplacer un seul profil."""
    target = safe_path(config / profile)
    settings = safe_path(state / 'noctalia/settings.toml')
    if snapshot(target) != before or (reset_gui and snapshot(settings) != settings_before):
        raise ValueError('Le profil ou les réglages GUI ont changé depuis le plan ; relancer')
    backups = state / 'cachy-setup/profiles'
    private_dir(state / 'cachy-setup')
    private_dir(backups)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + profile + '-', dir=str(backups)))
    print('Sauvegarde : ' + str(backup))
    record = {'version': 1, 'profile': profile, 'config': str(config), 'state': str(state),
              'before': before, 'after': snapshot(proposed), 'reset_gui': reset_gui,
              'settings_before': settings_before if reset_gui else None, 'status': 'préparation'}
    save_json(backup / 'manifest.json', record)
    # Garder aussi les journaux en cas de validation échouée avant remplacement.
    try:
        if before is not None:
            shutil.copytree(target, backup / 'before', copy_function=shutil.copy2)
            if snapshot(backup / 'before') != before:
                raise ValueError('Le profil a changé pendant la sauvegarde')
        if reset_gui and settings_before is not None:
            shutil.copy2(settings, backup / 'settings.before.toml')
            if snapshot(backup / 'settings.before.toml') != settings_before:
                raise ValueError('Réglages GUI modifiés pendant la sauvegarde')
        if provenance is not None:
            save_json(backup / 'kitty-source.json', provenance)
        with tempfile.TemporaryDirectory(prefix='.cachy-profile-', dir=str(config)) as temporary:
            stage = Path(temporary)
            if proposed.exists():
                shutil.copytree(proposed, stage / profile, copy_function=shutil.copy2)
                if snapshot(stage / profile) != record['after']:
                    raise ValueError('Copies préparées incohérentes')
                validator(profile, stage, backup / 'validation-before-copy')
            if snapshot(target) != before or (reset_gui and snapshot(settings) != settings_before):
                raise ValueError('Configuration modifiée pendant la validation ; aucun remplacement')
            # Le dossier précédent reste disponible même si la copie suivante échoue.
            if before is not None:
                os.replace(target, stage / 'previous')
            try:
                if proposed.exists():
                    os.replace(stage / profile, target)
            except OSError:
                if before is not None:
                    os.replace(stage / 'previous', target)
                raise
            record['status'] = 'profil remplacé'
            save_json(backup / 'manifest.json', record)
            if reset_gui and settings_before is not None:
                if snapshot(settings) != settings_before:
                    raise ValueError('Réglages GUI modifiés ; profil remplacé, réglages conservés')
                settings.unlink()
            if target.exists():
                validator(profile, config, backup / 'validation-installed')
        record['status'] = 'terminé'
    except Exception:
        record['status'] = 'échec ; examiner les empreintes et journaux avant restauration'
        raise
    finally:
        save_json(backup / 'manifest.json', record)
    print('Profil vérifié. Aucun paquet ni service modifié. Fermer/réouvrir les applications si nécessaire.')
    return backup


def update(args, config, state):
    if args.reset_gui and args.profile != 'noctalia':
        raise ValueError('--reset-gui concerne uniquement Noctalia')
    if args.fetch_kitty and args.profile != 'kitty':
        raise ValueError('--fetch-kitty concerne uniquement Kitty')
    if args.apply:
        check_target()
    target = safe_path(config / args.profile)
    before = snapshot(target)
    if before is not None and before['.']['type'] != 'dir':
        raise ValueError('Un dossier de profil est attendu')
    settings = safe_path(state / 'noctalia/settings.toml')
    gui = snapshot(settings) if args.profile == 'noctalia' else None
    if gui is not None:
        if gui['.']['type'] != 'file':
            raise ValueError('Un fichier de réglages GUI ordinaire est attendu')
        print('Réglages GUI prioritaires : ' + str(settings))
        print('RETRAIT après sauvegarde.' if args.reset_gui else 'CONSERVÉS : ils peuvent masquer les nouveaux réglages des modules.')
    files, provenance = prepare(args.profile, args.keyboard, args.variant, args.fetch_kitty or args.apply)
    if files is None:
        print('Kitty : source Masternaka/CachyOS/main. Aucun réseau ni écriture en --plan.')
        print('Ajouter --fetch-kitty pour lire le profil distant et ses différences (réseau explicite).')
        return
    # L'aperçu local reste en mémoire : aucun dossier temporaire n'est créé.
    show_memory_diff(target, before, files)
    if provenance:
        print('Commit Kitty : ' + provenance['commit'])
    if not args.apply:
        return
    if input('Pour remplacer ce seul profil après sauvegarde, saisir MODIFIER : ') != 'MODIFIER':
        raise ValueError('Annulé, aucun profil modifié')
    with operation_lock(state):
        safe_path(config)
        config.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.cachy-proposed-', dir=str(config)) as temporary:
            proposed = Path(temporary) / args.profile
            write_profile(files, proposed)
            transact(args.profile, config, state, proposed, before, gui, args.reset_gui, provenance)


def show_memory_diff(target, before, files):
    before = before or {}
    existing = {name for name, info in before.items() if info['type'] == 'file'}
    changed = 0
    for name in sorted(existing | set(files)):
        left = (target / name).read_bytes() if name in existing else b''
        right = files[name].encode('utf-8') if name in files else b''
        if name in existing and name in files and left == right:
            continue
        changed += 1
        print(('AJOUT ' if name not in existing else 'SUPPRESSION ' if name not in files else 'MODIFICATION ') + name)
        try:
            print(text_safe(''.join(difflib.unified_diff(left.decode('utf-8').splitlines(True),
                  right.decode('utf-8').splitlines(True), fromfile='actif/' + name, tofile='proposé/' + name))))
        except UnicodeDecodeError:
            print('Contenu binaire ; remplacement ou suppression signalé sans affichage.')
    if not changed:
        print('Aucune différence de contenu. En application, modes privés : dossiers 0700, fichiers 0600.')
    print('Remplacement du dossier entier : fichiers supplémentaires et dossiers vides non repris supprimés du profil actif après sauvegarde.')


def read_backup(folder, config, state):
    base = safe_path(state / 'cachy-setup/profiles')
    folder = safe_path(folder)
    if folder.parent != base or not folder.is_dir():
        raise ValueError('Choisir une sauvegarde directe du dossier utilisateur cachy-setup/profiles')
    manifest = safe_path(folder / 'manifest.json')
    record = json.loads(manifest.read_text())
    if record.get('version') != 1 or record.get('profile') not in PROFILES or record.get('config') != str(config) or record.get('state') != str(state):
        raise ValueError('Sauvegarde incompatible avec ce compte ou ces chemins XDG')
    if snapshot(folder / 'before') != record['before']:
        raise ValueError('Sauvegarde absente ou modifiée : restauration refusée')
    return record


def restore(args, config, state):
    if args.apply:
        check_target()
    folder = Path(args.backup).absolute()
    record = read_backup(folder, config, state)
    profile = record['profile']
    target = config / profile
    current = snapshot(target)
    if current != record['after']:
        raise ValueError('Le profil actif diffère de celui déployé : changements ultérieurs ou opération partielle. Examiner manuellement, aucun écrasement forcé.')
    show_diff(target, folder / 'before')
    if record['reset_gui']:
        print('Cette opération avait retiré les réglages GUI. Leur remise en place reste manuelle après comparaison : ' + str(folder / 'settings.before.toml'))
    if not args.apply:
        return
    if input('Pour restaurer ce seul profil après une nouvelle sauvegarde, saisir RESTAURER : ') != 'RESTAURER':
        raise ValueError('Annulé')
    with operation_lock(state):
        if read_backup(folder, config, state) != record:
            raise ValueError('La sauvegarde a changé depuis l’aperçu')
        transact(profile, config, state, folder / 'before', current, None)


def compare(prepared, config, state):
    """Aperçu des copies déjà préparées par l'installateur, sans nouvelle récupération."""
    prepared = safe_path(Path(prepared).absolute())
    for name in (*PROFILES, 'xdg-desktop-portal', 'mimeapps.list'):
        print('\nProfil : ' + name)
        if not (prepared / name).exists():
            raise ValueError('Copie préparée absente : ' + name)
        show_diff(config / name, prepared / name)
    settings = safe_path(state / 'noctalia/settings.toml')
    if settings.exists():
        print('Réglages GUI Noctalia prioritaires : ' + str(settings))
        print('Ils seront sauvegardés puis retirés par la réinstallation complète ; aucune fusion.')
    print('greetd et Greeter : remplacement selon le plan initial, sauvegarde système dans le dossier affiché par l’installateur.')


def run_read(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=15, env=dict(os.environ, LC_ALL='C', NO_COLOR='1'))


def diagnose(config, state, runner=run_read):
    issues = 0
    def report(label, ok, detail):
        nonlocal issues
        issues += not ok
        print(('CORRECT ' if ok else 'À VÉRIFIER ') + label + ' : ' + text_safe(detail.strip()))
    release = Path('/etc/os-release').read_text() if Path('/etc/os-release').is_file() else ''
    release = dict(line.split('=', 1) for line in release.splitlines() if '=' in line)
    target = platform.system() == 'Linux' and release.get('ID', '').strip('"\'') == 'cachyos' and not Path('/run/archiso').exists()
    report('plateforme', target, platform.system() + ' ; cible attendue : CachyOS installé')
    for pkg in ('umbriel', 'noctalia', 'noctalia-greeter', 'kitty', 'xdg-desktop-portal-umbriel'):
        try:
            result = runner(['pacman', '-Q', pkg])
            report('paquet ' + pkg, result.returncode == 0, result.stdout or result.stderr)
        except (OSError, subprocess.TimeoutExpired) as error:
            report('paquet ' + pkg, False, str(error))
    for profile in PROFILES:
        try:
            data = snapshot(config / profile)
            if data is None:
                raise ValueError('Profil absent')
            if profile == 'kitty':
                validate(profile, config, None)
                report(profile, True, 'Inclusions statiques vérifiées ; rendu non testé')
                continue
            command = ['/usr/bin/umbriel', 'config', 'validate', '--json'] if profile == 'umbriel' else ['/usr/bin/noctalia', 'config', 'validate', str(config / profile)]
            # Aucun dossier de logs, aucun helper Greeter, aucune réparation.
            result = runner(command)
            validate_native_result(profile, result)
            report(profile, True, 'Validateur natif sans diagnostic')
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            report(profile, False, str(error))
    commands = [(['systemctl', 'is-active', 'greetd.service'], 'Greeter'),
                (['systemctl', 'is-active', 'NetworkManager.service'], 'réseau'),
                (['systemctl', '--user', 'is-active', 'pipewire.socket', 'pipewire-pulse.socket', 'wireplumber.service', 'gnome-keyring-daemon.socket'], 'audio et trousseau'),
                (['systemctl', '--user', 'is-active', 'xdg-desktop-portal.service', 'xdg-desktop-portal-umbriel.service'], 'portails'),
                (['umbriel', 'outputs'], 'écrans détectés')]
    for command, label in commands:
        try:
            result = runner(command)
            # is-active renvoie zéro si UNE unité est active : vérifier toutes les lignes.
            lines = result.stdout.strip().splitlines()
            ok = result.returncode == 0
            if 'is-active' in command:
                ok = ok and len(lines) == len(command) - command.index('is-active') - 1 and all(line == 'active' for line in lines)
            report(label, ok, result.stdout or result.stderr)
        except (OSError, subprocess.TimeoutExpired) as error:
            report(label, False, str(error))
    if (state / 'noctalia/settings.toml').exists():
        report('priorité GUI', False, str(state / 'noctalia/settings.toml') + ' a priorité sur les modules')
    print('Diagnostic en lecture seule. Un service arrêté en TTY ou un portail non sollicité demande une vérification en session.')
    return 1 if issues else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    update_parser = sub.add_parser('update', help='Mettre à jour un seul profil ; aperçu par défaut')
    update_parser.add_argument('profile', choices=PROFILES)
    mode = update_parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--plan', action='store_true')
    update_parser.add_argument('--fetch-kitty', action='store_true', help='Autoriser la lecture GitHub pour un aperçu Kitty')
    update_parser.add_argument('--reset-gui', action='store_true', help='Retirer les réglages GUI Noctalia après sauvegarde')
    update_parser.add_argument('--keyboard', default='ca')
    update_parser.add_argument('--variant', default='')
    restore_parser = sub.add_parser('restore', help='Restaurer un profil sauvegardé ; aperçu par défaut')
    restore_parser.add_argument('backup')
    mode = restore_parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--plan', action='store_true')
    sub.add_parser('backups', help='Lister les sauvegardes utilisateur, sans sudo')
    sub.add_parser('diagnose', help='Diagnostic en lecture seule, sans réparation')
    compare_parser = sub.add_parser('compare', help='Comparer des copies utilisateur déjà préparées (auxiliaire de l’installateur)')
    compare_parser.add_argument('prepared')
    args = parser.parse_args()
    try:
        config, state = locations()
        if args.command == 'update':
            update(args, config, state)
        elif args.command == 'restore':
            restore(args, config, state)
        elif args.command == 'diagnose':
            return diagnose(config, state)
        elif args.command == 'compare':
            compare(args.prepared, config, state)
        else:
            folder = safe_path(state / 'cachy-setup/profiles')
            if not folder.exists():
                print('Aucune sauvegarde de mise à jour ciblée. Les sauvegardes de l’installation complète sont sous /var/lib/cachy-setup (guide du bureau).')
            else:
                for backup in sorted(folder.iterdir()):
                    print(str(backup))
        return 0
    except (OSError, ValueError, KeyError, EOFError, subprocess.TimeoutExpired) as error:
        print('Erreur : ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
