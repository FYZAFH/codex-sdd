import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.double_sdd.path_safety import (
    PathSafetyError,
    ensure_contained,
    reject_link_or_reparse,
    validate_worktrees_anchor,
)


class PathSafetyTests(unittest.TestCase):
    def test_ensure_contained_accepts_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self.assertTrue(ensure_contained(root / "child" / "file.txt", root))

    def test_ensure_contained_rejects_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sibling = root.parent / f"{root.name}-sibling"
            self.assertFalse(ensure_contained(sibling, root))

    def test_reject_link_or_reparse_rejects_symlink_when_supported(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            link = root / "link"
            try:
                os.symlink(target, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(PathSafetyError):
                reject_link_or_reparse(link, "link")

    def test_reject_link_or_reparse_rejects_mocked_reparse_point(self):
        reparse_attribute = 0x400
        mocked_stat = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=reparse_attribute,
        )

        with patch(
            "scripts.double_sdd.path_safety.stat.FILE_ATTRIBUTE_REPARSE_POINT",
            reparse_attribute,
            create=True,
        ), patch.object(
            Path,
            "lstat",
            return_value=mocked_stat,
        ):
            with self.assertRaises(PathSafetyError) as ctx:
                reject_link_or_reparse(Path("mocked-reparse"), "mocked path")

        self.assertIn("reparse point", str(ctx.exception))

    def test_validate_worktrees_anchor_requires_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / ".worktrees").write_text("not a directory", encoding="utf-8")
            with self.assertRaises(PathSafetyError):
                validate_worktrees_anchor(repo)

    def test_validate_worktrees_anchor_rejects_mount_point(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / ".worktrees").mkdir()
            with patch("scripts.double_sdd.path_safety.is_mount_point", return_value=True):
                with self.assertRaises(PathSafetyError) as ctx:
                    validate_worktrees_anchor(repo)
            self.assertIn("symlink, junction, mount point, or reparse point", str(ctx.exception))
