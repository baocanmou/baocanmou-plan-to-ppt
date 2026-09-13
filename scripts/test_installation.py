"""Regression tests for data preservation and avoiding duplicate Skill discovery."""
import tempfile
import unittest
from pathlib import Path
from install_skill import hashes, install, SOURCE


class InstallationTests(unittest.TestCase):
    def test_backup_is_outside_discovery_and_restorable(self):
        with tempfile.TemporaryDirectory() as td:
            destination = Path(td) / 'skills' / 'example'
            install(destination)
            (destination / 'local-edit.txt').write_text('keep me', encoding='utf-8')
            result = install(destination, replace=True)
            backup = Path(result['backup'])
            self.assertNotIn(destination.parent, backup.parents)
            self.assertEqual((backup / 'local-edit.txt').read_text(), 'keep me')
            self.assertEqual(len(list(destination.parent.rglob('SKILL.md'))), 1)
            self.assertEqual(hashes(destination), hashes(SOURCE))
            destination.rename(Path(td) / 'new-version')
            backup.rename(destination)
            self.assertEqual((destination / 'local-edit.txt').read_text(), 'keep me')

    def test_existing_directory_and_symlink_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            destination = Path(td) / 'skills' / 'example'
            install(destination)
            with self.assertRaises(ValueError):
                install(destination)
            link = destination.with_name('linked')
            link.symlink_to(destination, target_is_directory=True)
            with self.assertRaises(ValueError):
                install(link, replace=True)
            self.assertTrue(link.is_symlink())
            self.assertEqual(hashes(destination), hashes(SOURCE))

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as td:
            destination = Path(td) / 'skills' / 'example'
            result = install(destination, dry_run=True)
            self.assertTrue(result['dry_run'])
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
