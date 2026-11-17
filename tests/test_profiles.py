"""Mises à jour et restaurations dans des HOME temporaires, jamais sur la machine."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import profiles as P
import noctalia_dotfiles as D
try:
    import tomllib
except ImportError:
    from pip._vendor import tomli as tomllib


class ProfilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cachy-profiles-')
        self.addCleanup(self.tmp.cleanup)
        # /var est un lien sur macOS ; les fixtures utilisent le chemin physique.
        self.home = Path(self.tmp.name).resolve()
        self.config = self.home / '.config'
        self.state = self.home / '.local/state'
        self.config.mkdir()
        self.target = self.config / 'kitty'
        self.target.mkdir(mode=0o700)
        (self.target / 'kitty.conf').write_text('font_size 11\n')
        (self.target / 'personal.conf').write_text('# garder\n')
        self.proposed = self.home / 'proposed'
        P.write_profile({'kitty.conf': 'font_size 14\n'}, self.proposed)
        self.before = P.snapshot(self.target)
        self.args = argparse.Namespace(profile='kitty', apply=False, fetch_kitty=False,
                                       reset_gui=False, keyboard='ca', variant='')
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def transact(self, **kwargs):
        return P.transact('kitty', self.config, self.state, self.proposed, self.before, None, **kwargs)

    def test_kitty_plan_has_no_network_or_writes(self):
        before = P.snapshot(self.home)
        with patch.object(P, 'fetch_kitty', side_effect=AssertionError('réseau interdit')):
            P.update(self.args, self.config, self.state)
        self.assertEqual(P.snapshot(self.home), before)

    def test_local_plan_checks_toml_without_writing(self):
        self.args.profile = 'umbriel'
        original = D.check_files
        before = P.snapshot(self.home)
        with patch.object(P, 'check_files', side_effect=lambda files: original(files, tomllib)):
            P.update(self.args, self.config, self.state)
        self.assertEqual(P.snapshot(self.home), before)

    def test_explicit_remote_plan_keeps_commit_and_does_not_write(self):
        self.args.fetch_kitty = True
        before = P.snapshot(self.home)
        with patch.object(P, 'fetch_kitty', return_value=({'kitty.conf': 'font_size 14\n'}, {'commit': 'a' * 40})) as fetch:
            P.update(self.args, self.config, self.state)
            fetch.assert_called_once()
        self.assertEqual(P.snapshot(self.home), before)

    def test_diff_reports_deletions_and_neutralizes_terminal_controls(self):
        (self.target / 'kitty.conf').write_text('font_size 11\n\x1b[31m\n')
        output = []
        P.show_diff(self.target, self.proposed, output.append)
        self.assertTrue(any('SUPPRESSION personal.conf' in line for line in output))
        self.assertTrue(any('\\x1b[31m' in line for line in output))
        self.assertFalse(any('\x1b' in line for line in output))

    def test_symlinks_and_special_files_are_refused(self):
        (self.target / 'link').symlink_to(self.proposed)
        with self.assertRaises(ValueError):
            P.snapshot(self.target)
        (self.target / 'link').unlink()
        os.mkfifo(self.target / 'pipe')
        with self.assertRaises(ValueError):
            P.snapshot(self.target)

    def test_update_saves_previous_and_replaces_only_selected_profile(self):
        other = self.config / 'noctalia'
        other.mkdir()
        (other / 'config.toml').write_text('# inchangé\n')
        expected = P.snapshot(other)
        backup = self.transact()
        self.assertEqual((self.target / 'kitty.conf').read_text(), 'font_size 14\n')
        self.assertFalse((self.target / 'personal.conf').exists())
        self.assertEqual(P.snapshot(backup / 'before'), self.before)
        self.assertEqual(P.snapshot(other), expected)
        record = json.loads((backup / 'manifest.json').read_text())
        self.assertEqual(record['after'], P.snapshot(self.target))
        self.assertEqual(record['status'], 'terminé')
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)

    def test_change_since_preview_refuses_without_backup_creation(self):
        (self.target / 'kitty.conf').write_text('font_size 22\n')
        with self.assertRaisesRegex(ValueError, 'depuis le plan'):
            self.transact()
        self.assertFalse(self.state.exists())
        self.assertEqual((self.target / 'kitty.conf').read_text(), 'font_size 22\n')

    def test_native_failure_keeps_profile_and_logs_before_copy(self):
        def fail(profile, config, logs):
            logs.mkdir()
            (logs / 'kitty.log').write_text('diagnostic simulé')
            raise ValueError('échec natif simulé')
        with self.assertRaises(ValueError):
            self.transact(validator=fail)
        self.assertEqual(P.snapshot(self.target), self.before)
        backups = list((self.state / 'cachy-setup/profiles').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / 'validation-before-copy/kitty.log').exists())

    def test_edit_during_validation_is_not_overwritten(self):
        def edit(profile, config, logs):
            (self.target / 'personal.conf').write_text('modification concurrente')
        with self.assertRaisesRegex(ValueError, 'pendant la validation'):
            self.transact(validator=edit)
        self.assertEqual((self.target / 'personal.conf').read_text(), 'modification concurrente')

    def test_second_rename_failure_restores_previous_folder(self):
        real = os.replace
        def fail(source, destination):
            if Path(destination) == self.target and Path(source).name == 'kitty':
                raise OSError('copie refusée simulée')
            return real(source, destination)
        with patch.object(P.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                self.transact()
        self.assertEqual(P.snapshot(self.target), self.before)

    def test_restore_refuses_later_edits_and_tampered_backup(self):
        backup = self.transact()
        (self.target / 'kitty.conf').write_text('font_size 18\n')
        args = argparse.Namespace(backup=str(backup), apply=False)
        with self.assertRaisesRegex(ValueError, 'changements ultérieurs'):
            P.restore(args, self.config, self.state)
        (backup / 'before/kitty.conf').write_text('autre contenu')
        with self.assertRaisesRegex(ValueError, 'Sauvegarde absente ou modifiée'):
            P.read_backup(backup, self.config, self.state)

    def test_restore_preview_is_read_only_and_application_has_new_backup(self):
        backup = self.transact()
        args = argparse.Namespace(backup=str(backup), apply=False)
        before = P.snapshot(self.home)
        P.restore(args, self.config, self.state)
        self.assertEqual(P.snapshot(self.home), before)
        args.apply = True
        with patch.object(P, 'check_target'), patch('builtins.input', return_value='RESTAURER'):
            P.restore(args, self.config, self.state)
        self.assertEqual(P.snapshot(self.target), self.before)
        self.assertEqual(len(list((self.state / 'cachy-setup/profiles').iterdir())), 2)

    def test_restore_original_absence_removes_only_selected_profile(self):
        shutil_target = self.config / 'kitty'
        import shutil
        shutil.rmtree(shutil_target)
        backup = P.transact('kitty', self.config, self.state, self.proposed, None, None)
        args = argparse.Namespace(backup=str(backup), apply=True)
        with patch.object(P, 'check_target'), patch('builtins.input', return_value='RESTAURER'):
            P.restore(args, self.config, self.state)
        self.assertFalse(self.target.exists())

    def test_reset_gui_requires_explicit_option_and_backs_up_settings(self):
        self.args.profile = 'noctalia'
        self.args.apply = True
        settings = self.state / 'noctalia/settings.toml'
        settings.parent.mkdir(parents=True)
        settings.write_text('# personnel\n')
        for reset in (False, True):
            self.args.reset_gui = reset
            with patch.object(P, 'check_target'), patch.object(P, 'prepare', return_value=({'config.toml': '# source\n'}, None)), patch.object(P, 'transact') as transaction, patch('builtins.input', return_value='MODIFIER'):
                P.update(self.args, self.config, self.state)
                self.assertEqual(transaction.call_args.args[6], reset)
            self.assertTrue(settings.exists())
        proposed = self.home / 'noctalia-proposed'
        P.write_profile({'config.toml': '# source\n'}, proposed)
        saved = P.snapshot(settings)
        backup = P.transact('noctalia', self.config, self.state, proposed, None, saved, True, validator=lambda *a: None)
        self.assertFalse(settings.exists())
        self.assertEqual(P.snapshot(backup / 'settings.before.toml'), saved)

    def test_apply_on_macos_refuses_before_network(self):
        self.args.apply = True
        with patch.object(P.platform, 'system', return_value='Darwin'), patch.object(P, 'fetch_kitty', side_effect=AssertionError('réseau interdit')):
            with self.assertRaisesRegex(ValueError, 'CachyOS'):
                P.update(self.args, self.config, self.state)

    def test_lock_prevents_two_profile_operations(self):
        with P.operation_lock(self.state):
            with self.assertRaisesRegex(ValueError, 'autre opération'):
                with P.operation_lock(self.state):
                    self.fail('verrou ignoré')

    def test_native_validation_only_calls_selected_profile(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, '{"valid":true,"diagnostics":[]}', '')
        D.check_native_profiles(self.config, self.home / 'logs', runner=runner, profiles=('umbriel',))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], '/usr/bin/umbriel')

    def test_diagnostic_does_not_write_and_catches_inactive_member(self):
        before = P.snapshot(self.home)
        calls = []
        def runner(command):
            calls.append(command)
            if 'is-active' in command:
                count = len(command) - command.index('is-active') - 1
                return subprocess.CompletedProcess(command, 0, 'active\n' * (count - 1) + 'inactive\n', '')
            return subprocess.CompletedProcess(command, 0, 'simulation\n', '')
        self.assertEqual(P.diagnose(self.config, self.state, runner), 1)
        self.assertEqual(P.snapshot(self.home), before)
        self.assertFalse(any('enable' in command or 'start' in command or 'sudo' in command for command in calls))

    def test_backup_for_other_xdg_paths_is_refused(self):
        backup = self.transact()
        with self.assertRaises(ValueError):
            P.read_backup(backup, self.home / 'other', self.state)

    def test_compare_prepared_profiles_is_read_only_and_reports_gui_removal(self):
        prepared = self.home / 'prepared'
        D.write_files(D.render_files(kitty_files={'kitty.conf': 'font_size 14\n'}), prepared)
        settings = self.state / 'noctalia/settings.toml'
        settings.parent.mkdir(parents=True)
        settings.write_text('# prioritaire\n')
        before = P.snapshot(self.home)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            P.compare(prepared / 'user', self.config, self.state)
        self.assertEqual(P.snapshot(self.home), before)
        self.assertIn('SUPPRESSION personal.conf', out.getvalue())
        self.assertIn('Réglages GUI Noctalia prioritaires', out.getvalue())

    def test_cli_consultation_does_not_create_state(self):
        env = dict(os.environ, HOME=str(self.home), XDG_CONFIG_HOME=str(self.config), XDG_STATE_HOME=str(self.state))
        for name in ('NOCTALIA_CONFIG_HOME', 'NOCTALIA_STATE_HOME'):
            env.pop(name, None)
        before = P.snapshot(self.home)
        for arguments in (['--help'], ['update', 'kitty', '--plan'], ['backups']):
            result = subprocess.run([sys.executable, '-B', str(Path(P.__file__)), *arguments],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(P.snapshot(self.home), before)

    def test_native_timeout_leaves_a_diagnostic_log(self):
        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 60)
        logs = self.home / 'timeout-logs'
        with self.assertRaises(subprocess.TimeoutExpired):
            D.check_native_profiles(self.config, logs, runner=timeout, profiles=('umbriel',))
        self.assertIn('60', (logs / 'umbriel.log').read_text())


if __name__ == '__main__':
    unittest.main()
