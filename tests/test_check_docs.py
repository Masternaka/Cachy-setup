"""Liens et ancres des guides : contrôles sans accès réseau."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_docs as C


class DocumentationTests(unittest.TestCase):
    def test_real_documentation_has_no_missing_local_links(self):
        _, errors = C.check()
        self.assertEqual(errors, [])

    def test_accents_duplicate_headings_and_code_examples(self):
        anchors = C.anchors('# Écrans et clavier\n# Écrans et clavier\n```md\n# Exemple ignoré\n```\n')
        self.assertEqual(anchors, {'écrans-et-clavier', 'écrans-et-clavier-1'})

    def test_missing_anchor_file_and_escape_are_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'docs').mkdir()
            (root / 'AGENTS.md').write_text('# Guide\n')
            (root / 'README.md').write_text('[absent](perdu.md)\n[ancre](AGENTS.md#absente)\n[sortie](../ailleurs.md)\n```\n[faux](ignoré.md)\n```\n')
            count, errors = C.check(root)
            self.assertEqual(count, 3)
            self.assertEqual(len(errors), 3)


if __name__ == '__main__':
    unittest.main()
