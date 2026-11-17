"""Récupération Kitty simulée : ni GitHub, ni configuration personnelle utilisés."""
import contextlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import kitty_source as SOURCE
import noctalia_dotfiles as DOTFILES

COMMIT = 'a' * 40
ORIGINAL = {
    'kitty.conf': '# Thème personnel\ninclude ~/.config/kitty/themes/test.conf\nfont_size 12\n',
    'themes/test.conf': 'foreground #ffffff\n',
    'quick-access-terminal.conf': 'lines 20\n',
    'README.md': 'Documentation et provenance du thème\n',
}


def archive_bytes(files=ORIGINAL, commit=COMMIT, extra=()):
    stream = io.BytesIO()
    prefix = 'CachyOS-' + commit + '/' + SOURCE.SOURCE + '/'
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr(prefix, '')
        for name, content in files.items():
            archive.writestr(prefix + name, content)
        for name, content, mode in extra:
            entry = zipfile.ZipInfo(prefix + name)
            entry.create_system = 3
            entry.external_attr = mode << 16
            archive.writestr(entry, content)
    return stream.getvalue()


class KittySourceTests(unittest.TestCase):
    def retrieve(self, archive=None, commit=COMMIT):
        self.calls = []
        def fetch(url):
            self.calls.append(url)
            if '/commits/' in url:
                return json.dumps({'sha': commit}).encode()
            return archive if archive is not None else archive_bytes(commit=commit)
        return SOURCE.fetch_kitty(fetch)

    def test_main_is_resolved_once_and_archive_uses_that_commit(self):
        prepared, record = self.retrieve()
        self.assertTrue(self.calls[0].endswith('/commits/main'))
        self.assertTrue(self.calls[1].endswith('/zip/' + COMMIT))
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(record['branch'], 'main')
        self.assertEqual(record['commit'], COMMIT)
        self.assertIn('README.md', prepared)
        self.assertIn('quick-access-terminal.conf', prepared)

    def test_subsequent_retrieval_can_follow_a_new_main_commit(self):
        self.retrieve()
        _, record = self.retrieve(commit='b' * 40)
        self.assertEqual(record['commit'], 'b' * 40)

    def test_include_adaptation_preserves_options_comments_and_source(self):
        before = dict(ORIGINAL)
        prepared, record = self.retrieve()
        self.assertEqual(ORIGINAL, before)
        self.assertEqual(prepared['kitty.conf'], ORIGINAL['kitty.conf'].replace('~/.config/kitty/', ''))
        self.assertEqual(record['adapted_includes'][0]['to'], 'themes/test.conf')
        hashes = record['files']['kitty.conf']
        self.assertNotEqual(hashes['original_sha256'], hashes['prepared_sha256'])
        self.assertEqual(record['files']['themes/test.conf']['original_sha256'], record['files']['themes/test.conf']['prepared_sha256'])

    def test_invalid_commit_is_rejected_before_archive_download(self):
        for commit in ('main', '../other', None):
            with self.subTest(commit=commit), self.assertRaisesRegex(ValueError, 'Commit'):
                self.retrieve(commit=commit)
            self.assertEqual(len(self.calls), 1)

    def test_corrupt_or_missing_profile_is_rejected(self):
        for archive in (b'not a zip', archive_bytes({}), archive_bytes({'README.md': 'documentation'})):
            with self.subTest(archive=archive[:20]), self.assertRaises(ValueError):
                self.retrieve(archive)

    def test_missing_cycle_dynamic_and_external_includes_are_rejected(self):
        cases = [
            {'kitty.conf': 'include missing.conf\n'},
            {'kitty.conf': 'include ~/.config/kitty/themes/missing.conf\n'},
            {'kitty.conf': 'include loop.conf\n', 'loop.conf': 'include kitty.conf\n'},
            {'kitty.conf': 'include /etc/kitty/other.conf\n'},
            {'kitty.conf': 'geninclude command\n'},
            {'kitty.conf': 'include ../outside.conf\n'},
            {'kitty.conf': 'include child.txt\n', 'child.txt': 'include ../../outside\n'},
        ]
        for files in cases:
            with self.subTest(files=files), self.assertRaises(ValueError):
                self.retrieve(archive_bytes(files))

    def test_symlinks_special_and_traversal_archive_members_are_rejected(self):
        for name, mode in (('link.conf', stat.S_IFLNK | 0o777),
                           ('pipe', stat.S_IFIFO | 0o600),
                           ('../outside.conf', stat.S_IFREG | 0o644)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.retrieve(archive_bytes(extra=[(name, '/tmp/outside', mode)]))

    def test_duplicate_paths_and_limits_are_rejected(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Duplicate name:', category=UserWarning)
            duplicate = archive_bytes(extra=[('kitty.conf', 'duplicate', stat.S_IFREG | 0o644)])
        with self.assertRaisesRegex(ValueError, 'double'):
            self.retrieve(duplicate)
        with patch.object(SOURCE, 'MAX_FILE_SIZE', 3), self.assertRaisesRegex(ValueError, 'volumineux'):
            self.retrieve()
        with patch.object(SOURCE, 'MAX_FILES', 1), self.assertRaisesRegex(ValueError, 'volumineux'):
            self.retrieve()

    def test_network_failure_does_not_generate_partial_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'rendered'
            with patch.object(sys, 'argv', ['prepare', '--fetch-kitty', '--output', str(destination)]), \
                 patch.object(DOTFILES, 'fetch_kitty', side_effect=OSError('réseau indisponible')), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                DOTFILES.main()
            self.assertFalse(destination.exists())

    def test_existing_destination_refuses_network_and_preserves_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            marker = destination / 'personal'
            marker.write_text('à préserver')
            with patch.object(sys, 'argv', ['prepare', '--fetch-kitty', '--output', str(destination)]), \
                 patch.object(DOTFILES, 'fetch_kitty') as fetch, contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                DOTFILES.main()
            fetch.assert_not_called()
            self.assertEqual(marker.read_text(), 'à préserver')

    def test_default_print_and_render_never_fetch(self):
        with patch.object(DOTFILES, 'fetch_kitty') as fetch:
            self.assertNotIn('user/kitty/kitty.conf', DOTFILES.render_files())
            with patch.object(sys, 'argv', ['prepare', '--print']), contextlib.redirect_stdout(io.StringIO()) as out:
                DOTFILES.main()
            fetch.assert_not_called()
            self.assertIn('source externe', out.getvalue())

    def test_full_preparation_records_provenance_and_copies_all_kitty_files(self):
        prepared, record = self.retrieve()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'rendered'
            with patch.object(sys, 'argv', ['prepare', '--fetch-kitty', '--output', str(destination)]), \
                 patch.object(DOTFILES, 'fetch_kitty', return_value=(prepared, record)):
                DOTFILES.main()
            self.assertEqual(json.loads((destination / 'system/kitty-source.json').read_text())['commit'], COMMIT)
            for name, content in prepared.items():
                self.assertEqual((destination / 'user/kitty' / name).read_text(), content)


if __name__ == '__main__':
    unittest.main()
