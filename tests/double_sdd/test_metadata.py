import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.double_sdd.metadata import (
    MetadataError,
    find_single_preimplementation_metadata,
    metadata_relpath_for_run_id,
    read_metadata,
    validate_metadata_relpath,
    validate_reused_metadata,
    validate_run_id,
)
from scripts.double_sdd.path_safety import PathSafetyError


VALID_SHA = "a" * 40


def valid_metadata(run_id="20260708-test"):
    return {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "active",
        "mainBranch": "main",
        "mainBase": VALID_SHA,
        "featureBranch": None,
        "worktreePath": None,
        "metadataPath": f".worktrees/{run_id}.metadata.json",
        "preexistingTrackedCheckpoint": None,
        "temporaryCheckpoints": [],
        "preexistingUntracked": [],
        "preexistingIgnored": [],
    }


class MetadataTests(unittest.TestCase):
    def assert_bad_reused_metadata(self, data, metadata_relpath):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            with self.assertRaises(MetadataError) as ctx:
                validate_reused_metadata(data, metadata_relpath, repo, worktrees)
        message = str(ctx.exception)
        self.assertIn("Existing metadata is incomplete or not well-typed", message)
        self.assertIn("Stop and reconcile or replace the metadata file before continuing.", message)

    def test_validate_run_id_rejects_parent_segments(self):
        with self.assertRaises(MetadataError):
            validate_run_id("bad..run")

    def test_validate_run_id_rejects_windows_reserved_device_names(self):
        for run_id in ("con", "prn", "aux", "nul", "com1", "lpt1", "prn.foo"):
            with self.subTest(run_id=run_id):
                with self.assertRaises(MetadataError):
                    validate_run_id(run_id)
                with self.assertRaises(MetadataError):
                    metadata_relpath_for_run_id(run_id)

        for run_id in ("ok-prn", "prn-ok"):
            with self.subTest(run_id=run_id):
                self.assertEqual(validate_run_id(run_id), run_id)
                self.assertEqual(
                    metadata_relpath_for_run_id(run_id),
                    f".worktrees/{run_id}.metadata.json",
                )

    def test_metadata_relpath_for_run_id(self):
        self.assertEqual(
            metadata_relpath_for_run_id("abc-123"),
            ".worktrees/abc-123.metadata.json",
        )

    def test_validate_metadata_relpath_rejects_nested_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            with self.assertRaises(MetadataError):
                validate_metadata_relpath(".worktrees/nested/foo.metadata.json", repo, worktrees)

    def test_validate_metadata_relpath_rejects_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            (worktrees / "20260709-test.metadata.json").mkdir()

            with self.assertRaises(MetadataError) as ctx:
                validate_metadata_relpath(
                    ".worktrees/20260709-test.metadata.json",
                    repo,
                    worktrees,
                    require_existing=True,
                )

        self.assertIn("regular file", str(ctx.exception))

    def test_validate_metadata_relpath_rejects_textual_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            for relpath in ("./.worktrees/run.metadata.json", ".worktrees//run.metadata.json"):
                with self.subTest(relpath=relpath):
                    with self.assertRaises(MetadataError):
                        validate_metadata_relpath(relpath, repo, worktrees)

    def test_validate_metadata_relpath_rejects_unsafe_worktrees_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()

            with patch(
                "scripts.double_sdd.metadata.validate_worktrees_anchor",
                side_effect=PathSafetyError("unsafe anchor"),
                create=True,
            ) as validate_anchor:
                with self.assertRaises(MetadataError) as ctx:
                    validate_metadata_relpath(".worktrees/20260708-test.metadata.json", repo, worktrees)

            validate_anchor.assert_called_once_with(repo)
            self.assertIn("unsafe anchor", str(ctx.exception))

    def test_validate_reused_metadata_requires_all_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            data = valid_metadata()
            del data["temporaryCheckpoints"]
            with self.assertRaises(MetadataError):
                validate_reused_metadata(data, ".worktrees/20260708-test.metadata.json", repo, worktrees)

    def test_validate_reused_metadata_wraps_invalid_run_id(self):
        data = valid_metadata("bad..run")

        self.assert_bad_reused_metadata(data, ".worktrees/bad..run.metadata.json")

    def test_validate_reused_metadata_wraps_invalid_metadata_relpath(self):
        data = valid_metadata()

        self.assert_bad_reused_metadata(data, ".worktrees/nested/20260708-test.metadata.json")

    def test_read_metadata_normalizes_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.metadata.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(MetadataError):
                read_metadata(path)

    def test_find_single_preimplementation_metadata_skips_bad_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            (worktrees / "bad name.metadata.json").write_text("not json", encoding="utf-8")
            good = worktrees / "20260708-test.metadata.json"
            good.write_text(json.dumps(valid_metadata()), encoding="utf-8")
            self.assertEqual(
                find_single_preimplementation_metadata(repo, worktrees),
                ".worktrees/20260708-test.metadata.json",
            )

    def test_find_single_preimplementation_metadata_rejects_missing_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            malformed = valid_metadata()
            del malformed["status"]
            (worktrees / "20260708-test.metadata.json").write_text(
                json.dumps(malformed),
                encoding="utf-8",
            )

            with self.assertRaises(MetadataError) as ctx:
                find_single_preimplementation_metadata(repo, worktrees)

        message = str(ctx.exception)
        self.assertIn("Existing metadata is incomplete or not well-typed", message)
        self.assertIn("Stop and reconcile or replace the metadata file before continuing.", message)
        self.assertNotIn("0 active pre-implementation candidate", message)

    def test_find_single_preimplementation_metadata_rejects_malformed_before_valid_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            malformed = valid_metadata("20260708-broken")
            del malformed["status"]
            (worktrees / "20260708-broken.metadata.json").write_text(
                json.dumps(malformed),
                encoding="utf-8",
            )
            (worktrees / "20260708-good.metadata.json").write_text(
                json.dumps(valid_metadata("20260708-good")),
                encoding="utf-8",
            )

            with self.assertRaises(MetadataError) as ctx:
                find_single_preimplementation_metadata(repo, worktrees)

        message = str(ctx.exception)
        self.assertIn("Existing metadata is incomplete or not well-typed", message)
        self.assertIn("status", message)
        self.assertIn("Stop and reconcile or replace the metadata file before continuing.", message)

    def test_find_single_preimplementation_metadata_skips_completed_and_abandoned(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            for run_id, status in (
                ("20260708-abandoned", "abandoned"),
                ("20260708-completed", "completed"),
            ):
                metadata = valid_metadata(run_id)
                metadata["status"] = status
                metadata["featureBranch"] = f"feature/{run_id}"
                metadata["worktreePath"] = f".worktrees/feature-{run_id}"
                (worktrees / f"{run_id}.metadata.json").write_text(
                    json.dumps(metadata),
                    encoding="utf-8",
                )
            (worktrees / "20260708-active.metadata.json").write_text(
                json.dumps(valid_metadata("20260708-active")),
                encoding="utf-8",
            )

            self.assertEqual(
                find_single_preimplementation_metadata(repo, worktrees),
                ".worktrees/20260708-active.metadata.json",
            )

    def test_find_single_preimplementation_metadata_rejects_unsafe_worktrees_anchor_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            metadata_path = worktrees / "20260708-test.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata()), encoding="utf-8")

            with patch(
                "scripts.double_sdd.metadata.validate_worktrees_anchor",
                side_effect=PathSafetyError("unsafe anchor"),
                create=True,
            ) as validate_anchor, patch(
                "scripts.double_sdd.metadata.read_metadata",
                side_effect=AssertionError("metadata should not be read"),
            ) as read_metadata_mock:
                with self.assertRaises(MetadataError) as ctx:
                    find_single_preimplementation_metadata(repo, worktrees)

            validate_anchor.assert_called_once_with(repo)
            read_metadata_mock.assert_not_called()
            self.assertIn("unsafe anchor", str(ctx.exception))

    def test_find_single_preimplementation_metadata_rejects_directory_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            (worktrees / "20260709-test.metadata.json").mkdir()

            with patch(
                "scripts.double_sdd.metadata.read_metadata",
                side_effect=AssertionError("metadata directory should not be read"),
            ) as read_metadata_mock:
                with self.assertRaises(MetadataError) as ctx:
                    find_single_preimplementation_metadata(repo, worktrees)

            read_metadata_mock.assert_not_called()
            self.assertIn("regular file", str(ctx.exception))

    def test_find_single_preimplementation_metadata_checks_path_safety_before_bad_run_id_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            bad = worktrees / "00 bad.metadata.json"
            bad.write_text("not json", encoding="utf-8")
            good = worktrees / "20260708-test.metadata.json"
            good.write_text(json.dumps(valid_metadata()), encoding="utf-8")

            def reject_bad_path(path, label, allow_missing=False):
                if Path(path) == bad:
                    raise PathSafetyError("bad candidate safety checked")
                return None

            with patch("scripts.double_sdd.metadata.reject_link_or_reparse", side_effect=reject_bad_path):
                with self.assertRaises(MetadataError) as ctx:
                    find_single_preimplementation_metadata(repo, worktrees)
            self.assertIn("bad candidate safety checked", str(ctx.exception))

    def test_find_single_preimplementation_metadata_skips_uppercase_suffix_without_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            uppercase = worktrees / "20260708-bad.METADATA.JSON"
            uppercase.write_text("not json", encoding="utf-8")
            good = worktrees / "20260708-test.metadata.json"
            good.write_text(json.dumps(valid_metadata()), encoding="utf-8")

            real_glob = type(worktrees).glob

            def glob_with_uppercase_candidate(path, pattern):
                if path == worktrees and pattern == "*.metadata.json":
                    return iter((uppercase, good))
                return real_glob(path, pattern)

            def read_metadata_if_valid(path):
                self.assertNotEqual(Path(path), uppercase)
                return json.loads(Path(path).read_text(encoding="utf-8"))

            with patch.object(type(worktrees), "glob", glob_with_uppercase_candidate), patch(
                "scripts.double_sdd.metadata.read_metadata",
                side_effect=read_metadata_if_valid,
            ) as read_metadata_mock:
                self.assertEqual(
                    find_single_preimplementation_metadata(repo, worktrees),
                    ".worktrees/20260708-test.metadata.json",
                )

            read_metadata_mock.assert_called_once_with(good)
