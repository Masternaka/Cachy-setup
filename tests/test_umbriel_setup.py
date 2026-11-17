"""Contrôles isolés : aucun appel d'installation ou de configuration système."""
import os
import importlib.util
import json
import re
import shlex
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest

try:
    import tomllib
except ImportError:
    try:
        # Parseur déjà livré avec pip sur le Python 3.9 local, sans installation.
        from pip._vendor import tomli as tomllib
    except ImportError:
        tomllib = None

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/umbriel_setup.sh"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("noctalia_dotfiles", SCRIPT.with_name("noctalia_dotfiles.py"))
DOTFILES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOTFILES)


class ConsultationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cachy-noctalia-test-")
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Une cible volontairement incompatible empêche toute consultation du
        # système Linux hôte éventuel. Les commandes à effets sont interdites.
        self.stub("uname", "printf 'Darwin\\n'\n")
        for command in ("sudo", "pacman", "paru", "yay", "systemctl", "install",
                        "mkdir", "chmod", "cp", "tee"):
            self.stub(command, 'printf "%s\\n" "$0" >> "$FORBIDDEN_CALLS"\nexit 97\n')
        self.env = dict(os.environ, HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_STATE_HOME=str(self.home / ".local/state"),
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        FORBIDDEN_CALLS=str(self.root / "forbidden"))

    def tearDown(self):
        self.temporary.cleanup()

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o700)

    def run_script(self, *arguments):
        result = subprocess.run(["bash", str(SCRIPT), *arguments], env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertFalse((self.root / "forbidden").exists(), result.stdout + result.stderr)
        self.assertEqual(list(self.home.iterdir()), [], "Écriture dans le dossier personnel")
        return result

    def test_help_and_plan_have_no_effect(self):
        for arguments in (("--help",), (), ("--plan",)):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Points bloquants", result.stdout)
        self.assertIn("graphical.target", result.stdout)
        self.assertIn("No Desktop", result.stdout)
        self.assertIn("xdg-desktop-portal-umbriel", result.stdout)

    def test_apply_refuses_incompatible_target_before_sudo(self):
        result = self.run_script("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("points bloquants", result.stderr)

    def test_invalid_arguments_are_rejected(self):
        for arguments in (("--unknown",), ("--keyboard",),
                          ("--keyboard", 'ca"\n[evil]'),
                          ("--variant", "$(touch surprise)"),
                          ("--aur-helper", "paru")):
            with self.subTest(arguments=arguments):
                self.assertNotEqual(self.run_script(*arguments).returncode, 0)

    def test_ambiguous_or_overlapping_xdg_paths_are_rejected_without_writes(self):
        original = self.env.copy()
        for config, state in (
            (str(self.home / "../outside"), str(self.home / ".local/state")),
            (str(self.home) + "/.config/..", str(self.home / ".local/state")),
            (str(self.home) + "/./.config", str(self.home / ".local/state")),
            (str(self.home) + "//.config", str(self.home / ".local/state")),
            (str(self.home / ".config"), str(self.home / ".local/../outside")),
            (str(self.home / ".config"), str(self.home / ".config")),
            (str(self.home / ".config"), str(self.home / ".config/state")),
            (str(self.home / ".local/state/config"), str(self.home / ".local/state")),
            (str(self.home.parent / "home-other/config"), str(self.home / ".local/state")),
        ):
            with self.subTest(config=config, state=state):
                self.env = dict(original, XDG_CONFIG_HOME=config, XDG_STATE_HOME=state)
                result = self.run_script("--plan")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("Erreur", result.stderr)
        self.env = original

    def test_distinct_xdg_siblings_with_shared_prefix_are_accepted(self):
        self.env.update(XDG_CONFIG_HOME=str(self.home / "profile"),
                        XDG_STATE_HOME=str(self.home / "profile-state"))
        self.assertEqual(self.run_script("--plan").returncode, 0)

    def test_application_references_match_the_selected_packages(self):
        # Contrat entre les paquets choisis, leurs fichiers et les profils :
        # Zed est distribué sous le nom zeditor par Arch/CachyOS.
        applications = {
            "kitty": ("kitty", None), "firefox": ("firefox", "firefox.desktop"),
            "thunar": ("thunar", "thunar.desktop"), "micro": ("micro", None),
            "zed": ("zeditor", "dev.zed.Zed.desktop"),
            "firefox-i18n-fr": (None, None),
            "papers": ("papers", "org.gnome.Papers.desktop"),
            "loupe": ("loupe", "org.gnome.Loupe.desktop"),
            "mpv": ("mpv", "mpv.desktop"),
        }
        source = SCRIPT.read_text()
        selected = shlex.split(re.search(r"^PACKAGES_APPLICATIONS=\((.*)\)$", source, re.M)[1])
        binaries = {applications[pkg][0] for pkg in selected} - {None}
        # Le paquet Kitty fournit aussi le lanceur du terminal déroulant.
        if "kitty" in selected:
            binaries.add("kitten")
        desktops = {applications[pkg][1] for pkg in selected} - {None}
        files = DOTFILES.render_files()
        for command in re.findall(r'action = "spawn ([^\"]+)"', files["user/umbriel/cfg/keybinds.toml"]):
            executable = shlex.split(command)[0]
            self.assertIn(executable, binaries | {"noctalia"})
        for line in files["user/mimeapps.list"].splitlines():
            if "=" in line:
                self.assertIn(line.split("=", 1)[1].rstrip(";"), desktops)
        for association in ("application/pdf=org.gnome.Papers.desktop;",
                            "image/png=org.gnome.Loupe.desktop;",
                            "video/mp4=mpv.desktop;", "audio/mpeg=mpv.desktop;"):
            self.assertIn(association, files["user/mimeapps.list"].splitlines())
        if tomllib:
            # Les favoris du lanceur doivent aussi correspondre aux applications
            # réellement sélectionnées, et non à des identifiants d'un autre bureau.
            shell = tomllib.loads(files["user/noctalia/cfg/shell.toml"])
            self.assertTrue(set(shell["shell"]["launcher"]["pinned"]).issubset(desktops))
        checked_binaries = shlex.split(re.search(r"^for tool in (.*); do$", source, re.M)[1])
        checked_desktops = shlex.split(re.search(r"^for desktop in (.*); do$", source, re.M)[1])
        self.assertTrue(binaries.issubset(checked_binaries))
        self.assertEqual(set(checked_desktops), desktops)
        self.assertNotIn("mousepad", checked_binaries)

    def test_thunar_archive_support_has_a_manager_and_zip_tools(self):
        output = self.run_resolution("printf 'Repository : extra\\nVersion : 1.0-1\\n'\n")
        for package in ("thunar-archive-plugin", "xarchiver", "zip", "unzip"):
            self.assertIn("TARGET extra/" + package + "\n", output)

    def run_resolution(self, pacman_body):
        self.stub("pacman", pacman_body)
        source = SCRIPT.read_text()
        # Charger uniquement les données et le résolveur, sans le flux --apply
        # ni les diagnostics du système hôte.
        globals_part = source.split("\ndie()", 1)[0]
        function = source.split("resolve_packages() {", 1)[1].split("\n}\n", 1)[0]
        program = globals_part + "\nresolve_packages() {" + function + "\n}\n"
        program += '''
resolve_packages
if ((${#REPO_TARGETS[@]})); then printf 'TARGET %s\\n' "${REPO_TARGETS[@]}"; fi
if ((${#PACKAGE_SOURCES[@]})); then printf 'SOURCE %s\\n' "${PACKAGE_SOURCES[@]}"; fi
if ((${#BLOCKERS[@]})); then printf 'BLOCKER %s\\n' "${BLOCKERS[@]}"; fi
'''
        result = subprocess.run(["bash", "-s"], input=program, env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "forbidden").exists())
        self.assertEqual(list(self.home.iterdir()), [])
        return result.stdout

    def test_repository_provenance_is_preserved_without_aur(self):
        output = self.run_resolution('''
[ "$1" = -Si ] || exit 97
case "$2" in
  umbriel|noctalia-greeter|xdg-desktop-portal-umbriel) repo=cachyos ;;
  *) repo=cachyos-extra-v3 ;;
esac
printf 'Repository      : %s\\nName            : %s\\nVersion         : 1:5.4.1-1\\n' "$repo" "$2"
''')
        self.assertIn("TARGET cachyos/umbriel\n", output)
        self.assertIn("TARGET cachyos/xdg-desktop-portal-umbriel\n", output)
        self.assertIn("TARGET cachyos-extra-v3/noctalia\n", output)
        self.assertIn("SOURCE noctalia | cachyos-extra-v3 | 1:5.4.1-1", output)
        self.assertNotIn("BLOCKER", output)
        self.assertNotIn("umbriel-git", output)

    def test_missing_repository_package_blocks_without_aur(self):
        output = self.run_resolution('''
[ "$1" = -Si ] || exit 97
if [ "$2" = umbriel ]; then exit 1; fi
printf 'Repository : extra\\nVersion : 1.0-1\\n'
''')
        self.assertIn("BLOCKER Paquet absent des bases locales : umbriel", output)
        self.assertIn("Aucun recours à l'AUR", output)
        self.assertNotIn("TARGET extra/umbriel\n", output)

    def test_unreadable_provenance_is_rejected(self):
        output = self.run_resolution("printf 'Version : 1.0-1\\n'\n")
        self.assertIn("Provenance ou version illisible pour umbriel", output)
        self.assertNotIn("TARGET ", output)

    def test_configuration_starts_current_shell(self):
        for options, layout, variant in (((), "ca", ""),
                                        (("--keyboard", "ca", "--variant", "multix"), "ca", "multix"),
                                        (("--keyboard", "us"), "us", "")):
            with self.subTest(layout=layout, variant=variant):
                result = self.run_script("--print-config", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('autostart = ["noctalia"]', result.stdout)
                self.assertEqual(result.stdout.count('layout = "' + layout + '"'), 2)
                self.assertEqual(result.stdout.count('variant = "' + variant + '"'), 2)
                self.assertIn('"Mod+Return" = { action = "spawn kitty", repeat = false }', result.stdout)
        result = self.run_script("--plan")
        self.assertIn("Clavier Umbriel et Greeter : ca / défaut", result.stdout)

    @unittest.skipUnless(tomllib, "Analyse TOML : aucun parseur déjà disponible")
    def test_configuration_is_valid_toml(self):
        for layout, variant in (("ca", ""), ("us", ""), ("ca", "multix")):
            files = DOTFILES.render_files(layout, variant)
            DOTFILES.check_files(files, toml_parser=tomllib)
            session = tomllib.loads(files["user/umbriel/cfg/input.toml"])
            greeter = tomllib.loads(files["system/greeter.toml"])
            self.assertEqual(session["input"]["keyboard"]["layout"], layout)
            self.assertEqual(greeter["keyboard"], {"layout": layout, "variant": variant})
            # Paramètres présents dans l'exemple officiel Greeter v1.7.0.
            self.assertEqual(greeter["clock"], {
                "enabled": True, "position": "above-panel",
                "time_format": "{:%H:%M}", "date_format": "%A, %x",
            })
            self.assertEqual(greeter["session"]["default"], "Umbriel")
            self.assertFalse(greeter["auth"]["allow_empty_password"])
        defaults = DOTFILES.render_files()
        session = tomllib.loads(defaults["user/umbriel/cfg/input.toml"])
        greeter = tomllib.loads(defaults["system/greeter.toml"])
        self.assertEqual(session["input"]["keyboard"]["layout"], "ca")
        self.assertEqual(session["input"]["keyboard"]["variant"], "")
        self.assertEqual(greeter["keyboard"], {"layout": "ca", "variant": ""})

    def run_network_check(self, active, enabled="", instance_status=0):
        self.stub("systemctl", '''
case "$1" in
  is-active) case " $ACTIVE_UNITS " in *" $3 "*) exit 0;; *) exit 3;; esac ;;
  list-unit-files) printf '%s' "$ENABLED_UNITS" ;;
  list-units)
    [ "$INSTANCE_STATUS" = 0 ] || exit "$INSTANCE_STATUS"
    for unit in $ACTIVE_UNITS; do
      case "$unit" in dhcpcd@*.service) printf '%s loaded active running DHCP\\n' "$unit";; esac
    done ;;
  *) exit 97 ;;
esac
''')
        function = SCRIPT.read_text().split("check_network_backend() {", 1)[1].split("\n}\n", 1)[0]
        program = 'set -eu\nBLOCKERS=()\ncheck_network_backend() {' + function + '''
}
check_network_backend
if ((${#BLOCKERS[@]})); then printf '%s\\n' "${BLOCKERS[@]}"; fi
'''
        env = dict(self.env, ACTIVE_UNITS=active, ENABLED_UNITS=enabled,
                   INSTANCE_STATUS=str(instance_status))
        result = subprocess.run(["bash", "-s"], input=program, env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_networkmanager_can_keep_its_iwd_backend(self):
        self.assertEqual(self.run_network_check("NetworkManager.service iwd.service"), "")

    def test_competing_network_backend_blocks_migration(self):
        self.assertIn("Gestionnaire réseau actif", self.run_network_check("systemd-networkd.service"))
        self.assertIn("dhcpcd@enp1s0.service", self.run_network_check("", "dhcpcd@enp1s0.service enabled disabled\n"))
        self.assertIn("iwd actif sans NetworkManager", self.run_network_check("iwd.service"))

    def test_active_dhcpcd_instance_blocks_even_without_enablement(self):
        self.assertIn("Gestionnaire réseau actif : dhcpcd@enp1s0.service",
                      self.run_network_check("dhcpcd@enp1s0.service"))

    def test_failed_instance_diagnostic_blocks_migration(self):
        self.assertIn("diagnostic réseau incomplet", self.run_network_check("", instance_status=1))


class NativeGateTests(unittest.TestCase):
    def run_gate(self, noctalia_output="Config is valid\n", report=None, returncode=0):
        if report is None:
            report = {"valid": True, "diagnostics": []}
        self.calls = []
        def runner(command, **kwargs):
            self.calls.append((command, kwargs))
            if command[0].endswith("noctalia"):
                return subprocess.CompletedProcess(command, returncode, noctalia_output, "")
            return subprocess.CompletedProcess(command, 0, json.dumps(report), "")
        with tempfile.TemporaryDirectory(prefix="cachy-native-gate-") as temporary:
            root = Path(temporary)
            DOTFILES.check_native_profiles(root / "config", root / "logs", runner=runner)
            self.assertTrue((root / "logs/noctalia.log").exists())
            self.assertTrue((root / "logs/umbriel.log").exists())
            self.assertEqual(self.calls[1][1]["env"]["XDG_CONFIG_HOME"], str((root / "config").resolve()))
            self.assertEqual(self.calls[0][0][-1], str((root / "config/noctalia").resolve()))

    def test_native_commands_validate_the_prepared_profile(self):
        self.run_gate()

    def test_noctalia_warning_is_blocking_even_with_exit_zero(self):
        with self.assertRaisesRegex(ValueError, "Avertissement Noctalia"):
            self.run_gate("\x1b[33mWARN config.toml:1: unknown setting\x1b[0m\nConfig is valid\n")

    def test_native_error_is_blocking(self):
        with self.assertRaisesRegex(ValueError, "Validation native échouée"):
            self.run_gate("ERROR invalid config\n", returncode=1)

    def test_umbriel_warning_is_blocking(self):
        with self.assertRaisesRegex(ValueError, "Diagnostic Umbriel"):
            self.run_gate(report={"valid": True, "diagnostics": [{"severity": "warning", "message": "unknown key"}]})

    def test_pam_inherited_systemd_session_is_accepted(self):
        with tempfile.TemporaryDirectory(prefix="cachy-pam-") as temporary:
            root = Path(temporary)
            (root / "greetd").write_text("auth include system-local-login\nsession include system-local-login\n")
            (root / "system-local-login").write_text("session include system-login\n")
            (root / "system-login").write_text("-session optional pam_systemd.so\n")
            original = {p: p.read_bytes() for p in root.iterdir()}
            DOTFILES.check_pam_session(root)
            self.assertEqual(original, {p: p.read_bytes() for p in root.iterdir()})

    def test_pam_cycle_or_auth_only_reference_cannot_validate_a_session(self):
        with tempfile.TemporaryDirectory(prefix="cachy-pam-bad-") as temporary:
            root = Path(temporary)
            (root / "greetd").write_text("auth optional pam_systemd.so\nsession include loop\n")
            (root / "loop").write_text("session include greetd\n")
            with self.assertRaisesRegex(ValueError, "pam_systemd.so"):
                DOTFILES.check_pam_session(root)


class ModuleTests(unittest.TestCase):
    def test_rendering_preserves_sources_and_synchronizes_keyboards(self):
        before = {p: p.read_bytes() for p in DOTFILES.ROOT.rglob("*") if p.is_file()}
        files = DOTFILES.render_files("ca", "multix")
        for path in ("user/umbriel/cfg/input.toml", "system/greeter.toml"):
            self.assertIn('layout = "ca"', files[path])
            self.assertIn('variant = "multix"', files[path])
        self.assertTrue(all("@KEYBOARD@" not in content for content in files.values()))
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_all_native_includes_exist(self):
        # Ce contrôle de chemins reste disponible même sans parseur TOML local.
        import re
        files = DOTFILES.render_files()
        for profile in ("umbriel", "noctalia"):
            root = "user/" + profile + "/"
            entry = files[root + "config.toml"].split("[include.optional]")[0]
            for include in re.findall(r'"(cfg/[^\"]+)"', entry):
                self.assertIn(root + include, files)
        self.assertNotIn("user/kitty/kitty.conf", files, "Kitty doit provenir du dépôt externe, sans récupération implicite")

    def test_staging_writes_only_a_new_directory(self):
        with tempfile.TemporaryDirectory(prefix="cachy-modules-") as temporary:
            destination = Path(temporary) / "prepared"
            files = DOTFILES.render_files("ca", "multix")
            DOTFILES.write_files(files, destination)
            for name, content in files.items():
                self.assertEqual((destination / name).read_text(), content)
            with self.assertRaises(FileExistsError):
                DOTFILES.write_files(files, destination)

    def test_rendering_rejects_source_links(self):
        with tempfile.TemporaryDirectory(prefix="cachy-source-link-") as temporary:
            root = Path(temporary)
            (root / "outside").symlink_to(SCRIPT)
            with self.assertRaisesRegex(ValueError, "Lien symbolique"):
                DOTFILES.render_files(root=root)

    def test_invalid_keyboard_does_not_write(self):
        with self.assertRaises(ValueError):
            DOTFILES.render_files('ca"\n[bad]')

    def test_replacing_profiles_preserves_previous_files_in_backup(self):
        with tempfile.TemporaryDirectory(prefix="cachy-deploy-fixture-") as temporary:
            root = Path(temporary)
            home = root / "home"
            config = home / ".config"
            state = home / ".local/state/noctalia"
            config.mkdir(parents=True)
            state.mkdir(parents=True)
            (config / "noctalia").mkdir()
            (config / "noctalia/old.toml").write_text("ancien profil")
            (config / "unrelated").mkdir()
            (config / "unrelated/personal").write_text("à préserver")
            (state / "settings.toml").write_text("réglage GUI prioritaire")
            stage = root / "prepared"
            kitty_fixture = {"kitty.conf": "include themes/test.conf\n",
                             "themes/test.conf": "foreground #ffffff\n"}
            DOTFILES.write_files(DOTFILES.render_files(kitty_files=kitty_fixture), stage)
            backup = root / "backup"
            backup.mkdir()
            function = SCRIPT.read_text().split("install_user_dotfiles() {", 1)[1].split("\n}\n", 1)[0]
            # Seule cette fonction de copie est chargée. sudo est remplacé dans
            # le processus enfant ; tous les chemins restent dans la fixture.
            program = '''set -eu
sudo() { "$@"; }
CONFIG_ITEMS=(umbriel noctalia kitty xdg-desktop-portal mimeapps.list)
install_user_dotfiles() {''' + function + '\n}\ninstall_user_dotfiles "$PREPARED"\n'
            env = dict(os.environ, CONFIG_HOME=str(config), BACKUP=str(backup),
                       GUI_SETTINGS=str(state / "settings.toml"), PREPARED=str(stage))
            result = subprocess.run(["bash", "-s"], input=program, text=True,
                                    env=env, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((backup / "replaced-user/noctalia/old.toml").read_text(), "ancien profil")
            self.assertFalse((config / "noctalia/old.toml").exists())
            self.assertTrue((config / "noctalia/cfg/bar.toml").is_file())
            self.assertEqual((config / "unrelated/personal").read_text(), "à préserver")
            self.assertEqual((backup / "noctalia-settings-replaced.toml").read_text(), "réglage GUI prioritaire")
            self.assertFalse((state / "settings.toml").exists())


if __name__ == "__main__":
    unittest.main()
