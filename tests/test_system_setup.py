"""Tests isolés SSH/disques : aucun service ni périphérique réel utilisé."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SSH = ROOT / 'scripts/ssh_setup.sh'
DISK = ROOT / 'scripts/disk_setup.sh'

FAKE_SYSTEMCTL = r'''import json, os, sys
from pathlib import Path
root = Path(os.environ['FIXTURE'])
a = sys.argv[1:]
state = json.loads((root / 'state').read_text())
with (root / 'calls').open('a') as out: out.write(json.dumps(a) + '\n')
if a[0] == 'show':
    values = state if a[1] == 'sshd.service' else dict(LoadState='not-found', UnitFileState='', ActiveState='inactive')
    if a[1] == 'sshd.socket' and os.environ.get('SOCKET'):
        values.update(LoadState='loaded', UnitFileState='enabled', ActiveState='active')
    for k, v in values.items(): print(k + '=' + v)
    sys.exit(0)
if os.environ.get('FAIL_ACTION') == a[0]: sys.exit(1)
if a[0] == 'enable': state['UnitFileState'] = 'enabled-runtime' if '--runtime' in a else 'enabled'
if a[0] == 'disable': state['UnitFileState'] = 'disabled'
if a[0] == 'start': state['ActiveState'] = 'active'
if a[0] == 'stop': state['ActiveState'] = 'inactive'
(root / 'state').write_text(json.dumps(state))
'''


class SystemSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cachy-system-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        tool = self.bin / 'systemctl'
        tool.write_text('#!' + sys.executable + '\n' + FAKE_SYSTEMCTL)
        tool.chmod(0o700)
        self.state = dict(LoadState='loaded', UnitFileState='disabled', ActiveState='inactive',
                          FragmentPath='/usr/lib/systemd/system/sshd.service', DropInPaths='')
        (self.root / 'state').write_text(json.dumps(self.state))
        self.env = dict(os.environ, FIXTURE=str(self.root), SSH_SCRIPT=str(SSH),
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def shell(self, code, env=None):
        return subprocess.run(['bash', '-s'], input=code, env=env or self.env,
                              capture_output=True, text=True, timeout=10)

    def ssh(self, body='read_state\napply_ssh\n', **options):
        state = dict(self.state, **options.pop('state', {}))
        (self.root / 'state').write_text(json.dumps(state))
        env = dict(self.env, **options)
        # sudo n'est jamais appelé. Cette fonction n'autorise que des écritures
        # dans la fixture, le faux systemctl et un résultat simulé pour sshd -t.
        return self.shell(r'''
source "$SSH_SCRIPT"
SSH_BACKUP_ROOT="$FIXTURE/backups"
sudo() {
  case "$1" in
    /usr/bin/sshd) return "${SSHD_STATUS:-0}" ;;
    systemctl) shift; command systemctl "$@" ;;
    install|mktemp|tee|chmod)
      local last="${!#}"
      [[ $last == "$FIXTURE/"* ]] || return 97
      command "$@" ;;
    *) return 97 ;;
  esac
}
''' + body, env)

    def actions(self):
        path = self.root / 'calls'
        return [a for a in map(json.loads, path.read_text().splitlines()) if a[0] != 'show'] if path.exists() else []

    def disk_functions(self, names, body, **options):
        source = DISK.read_text()
        functions = '\n'.join(name + '() {' + source.split(name + '() {', 1)[1].split('\n}\n', 1)[0] + '\n}' for name in names)
        prefix = "set -eu\nfatal() { printf '%s\\n' \"$*\" >&2; exit 1; }\n"
        return self.shell(prefix + functions + '\n' + body, dict(self.env, **options))

    def test_help_has_no_system_effect(self):
        for path in (SSH, DISK):
            result = subprocess.run(['bash', str(path), '--help'], env=self.env,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / 'calls').exists())

    def test_ssh_already_enabled_and_active_is_noop(self):
        result = self.ssh(state=dict(UnitFileState='enabled', ActiveState='active'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.actions(), [])
        self.assertFalse((self.root / 'backups').exists())

    def test_ssh_enabled_but_inactive_only_starts(self):
        result = self.ssh(state=dict(UnitFileState='enabled'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.actions(), [['start', 'sshd.service']])

    def test_ssh_active_but_disabled_only_enables_without_restart(self):
        result = self.ssh(state=dict(ActiveState='active'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.actions(), [['enable', 'sshd.service']])

    def test_ssh_invalid_config_prevents_all_mutations(self):
        self.assertNotEqual(self.ssh(SSHD_STATUS='1').returncode, 0)
        self.assertEqual(self.actions(), [])
        self.assertFalse((self.root / 'backups').exists())

    def test_ssh_refuses_masked_custom_unstable_and_socket_states(self):
        for state in (dict(UnitFileState='masked'), dict(ActiveState='activating'),
                      dict(DropInPaths='/etc/systemd/system/sshd.service.d/custom.conf')):
            self.assertNotEqual(self.ssh(state=state).returncode, 0)
        self.assertNotEqual(self.ssh(SOCKET='1').returncode, 0)
        self.assertEqual(self.actions(), [])

    def test_ssh_failed_start_leaves_journal_and_reports_partial_state(self):
        result = self.ssh(FAIL_ACTION='start')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('potentiellement partiel', result.stderr)
        self.assertTrue(list((self.root / 'backups').glob('*/retour-arriere.sh')))
        self.assertNotIn(['stop', 'sshd.service'], self.actions())

    def test_ssh_undo_restores_runtime_enablement(self):
        initial = dict(self.state, UnitFileState='enabled-runtime', ActiveState='active')
        result = self.ssh(state=initial)
        self.assertEqual(result.returncode, 0, result.stderr)
        undo = next((self.root / 'backups').glob('*/retour-arriere.sh'))
        self.assertEqual(undo.stat().st_mode & 0o777, 0o600)
        result = self.shell(undo.read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'state').read_text()), initial)

    def test_disk_identity_mounted_readonly_and_type_guards(self):
        body = r'''
blkid() { case " $* " in *" UUID "*) printf '%s\n' "${ACTUAL_UUID:-expected}";; *) printf '%s\n' "${FS_TYPE:-ext4}";; esac; }
lsblk() { printf '%s\n' "${NODE:-8:1}"; }
blockdev() { printf '%s\n' "${RO:-0}"; }
findmnt() { printf '%s' "${MOUNTED:-}"; }
require_offline_device /dev/fixture expected 8:1
'''
        names = ['mounted_device_numbers', 'require_offline_device']
        self.assertEqual(self.disk_functions(names, body).returncode, 0)
        for env in (dict(ACTUAL_UUID='other'), dict(FS_TYPE='btrfs'), dict(NODE='8:2'), dict(RO='1'), dict(MOUNTED='8:1\n')):
            with self.subTest(env=env):
                self.assertNotEqual(self.disk_functions(names, body, **env).returncode, 0)

    def plan_fstab(self, contents):
        path = self.root / 'fstab'
        path.write_text(contents)
        body = '''
FSTAB="$FIXTURE/fstab"
UUIDS=(a b c d)
LABELS=('Backup Medias' 'Disque Samsung' Medias SSD)
DEVICES=(/dev/fixture1 /dev/fixture2 /dev/fixture3 /dev/fixture4)
BOOT_MOUNT_OPTIONS=defaults,nofail
# Fonctions sans effet : aucun dossier /mnt ni périphérique réel n'est consulté.
check_mount_directory() { :; }
findfs() { return 1; }
realpath() { printf '%s\\n' "${!#}"; }
sha256sum() { cksum "${!#}"; }
plan_boot_mounts
printf '%s\\n' "${FSTAB_LINES[@]}"
'''
        return self.disk_functions(['plan_boot_mounts'], body)

    def test_disk_fstab_preserves_existing_lines_and_escapes_spaces(self):
        original = '# exemple\nUUID=system / ext4 defaults 0 1\n'
        result = self.plan_fstab(original)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('/mnt/Backup\\040Medias ext4 defaults,nofail 0 2', result.stdout)
        self.assertEqual((self.root / 'fstab').read_text(), original)

    def test_disk_identical_fstab_entry_is_reused(self):
        result = self.plan_fstab('UUID=a /mnt/Backup\\040Medias ext4 defaults,nofail 0 2\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('UUID=a ', result.stdout)

    def test_disk_conflicting_or_nested_fstab_entry_is_refused(self):
        for line in ('UUID=a /data ext4 defaults 0 2\n',
                     'UUID=other /mnt/Medias ext4 defaults 0 2\n',
                     'UUID=other /mnt/Medias/sub ext4 defaults 0 2\n'):
            self.assertNotEqual(self.plan_fstab(line).returncode, 0)


if __name__ == '__main__':
    unittest.main()
