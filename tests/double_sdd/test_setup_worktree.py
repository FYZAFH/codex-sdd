import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.double_sdd.setup_worktree import (
    SetupError,
    _blocking_empty_directories,
    determine_metadata_relpath,
    main,
    setup_worktree,
    success_payload,
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


class SetupWorktreeTests(unittest.TestCase):
    def test_rejects_run_id_without_direct_mode(self):
        with self.assertRaises(SetupError):
            determine_metadata_relpath(
                repo=Path.cwd(),
                worktrees_dir=Path.cwd() / ".worktrees",
                metadata_path="",
                run_id="manual",
                no_upstream_metadata=False,
            )

    def test_rejects_metadata_path_with_direct_mode(self):
        with self.assertRaises(SetupError):
            determine_metadata_relpath(
                repo=Path.cwd(),
                worktrees_dir=Path.cwd() / ".worktrees",
                metadata_path=".worktrees/run.metadata.json",
                run_id="run",
                no_upstream_metadata=True,
            )

    def test_mode_mixing_rejects_before_lookup_or_read(self):
        with patch(
            "scripts.double_sdd.setup_worktree.find_single_preimplementation_metadata",
            side_effect=AssertionError("lookup should not run"),
        ) as lookup, patch(
            "scripts.double_sdd.setup_worktree.read_metadata",
            side_effect=AssertionError("metadata should not be read"),
        ) as read:
            with self.assertRaises(SetupError):
                determine_metadata_relpath(
                    repo=Path.cwd(),
                    worktrees_dir=Path.cwd() / ".worktrees",
                    metadata_path=".worktrees/run.metadata.json",
                    run_id="run",
                    no_upstream_metadata=False,
                )
            with self.assertRaises(SetupError):
                determine_metadata_relpath(
                    repo=Path.cwd(),
                    worktrees_dir=Path.cwd() / ".worktrees",
                    metadata_path="",
                    run_id="run",
                    no_upstream_metadata=False,
                )

        lookup.assert_not_called()
        read.assert_not_called()

    def test_main_rejects_missing_branch(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(main([]), 0)

    def test_main_normalizes_worktrees_mkdir_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                raise AssertionError(f"unexpected git call: {args!r}")

            real_mkdir = type(repo).mkdir

            def fail_worktrees_mkdir(path, mode=0o777, parents=False, exist_ok=False):
                if Path(path) == worktrees:
                    raise PermissionError("mkdir denied")
                return real_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

            out = io.StringIO()
            err = io.StringIO()
            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ), patch.object(type(repo), "mkdir", fail_worktrees_mkdir), contextlib.redirect_stdout(
                out
            ), contextlib.redirect_stderr(err):
                code = main(
                    [
                        "--branch",
                        "feature/manual",
                        "--run-id",
                        "manual",
                        "--no-upstream-metadata",
                    ]
                )

            self.assertNotEqual(code, 0)
            self.assertEqual(out.getvalue(), "")
            self.assertTrue(err.getvalue().startswith("error: "), err.getvalue())
            self.assertIn("failed to create repo-local .worktrees directory", err.getvalue())
            self.assertIn("Repair permissions or remove the blocking path", err.getvalue())

    def test_success_output_is_json_shape(self):
        payload = success_payload(
            metadata_path=".worktrees/run.metadata.json",
            worktree_path=".worktrees/feature-run",
            branch="feature/run",
        )
        self.assertEqual(
            json.loads(payload),
            {
                "metadataPath": ".worktrees/run.metadata.json",
                "worktreePath": ".worktrees/feature-run",
                "featureBranch": "feature/run",
            },
        )

    def test_direct_mode_refuses_dirty_state_without_creating_metadata(self):
        cases = (
            ("tracked", {"tracked": " M tracked.txt\n"}),
            ("untracked", {"untracked": "notes.txt\n"}),
            ("ignored", {"ignored": "build.log\n"}),
        )
        for name, state in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp).resolve()
                metadata_path = repo / ".worktrees" / "manual.metadata.json"

                with patch(
                    "scripts.double_sdd.setup_worktree._run_git",
                    side_effect=self.fake_git_for_direct_dirty(repo, state),
                ), patch(
                    "scripts.double_sdd.setup_worktree._git_success",
                    side_effect=self.fake_git_success_clean_preflight,
                ):
                    with self.assertRaises(SetupError) as ctx:
                        setup_worktree(
                            "feature/manual",
                            run_id="manual",
                            no_upstream_metadata=True,
                            cwd=repo,
                        )

                self.assertFalse(metadata_path.exists())
                self.assertIn("Direct-entry metadata creation cannot safely record", str(ctx.exception))

    def test_direct_mode_existing_target_branch_fails_without_creating_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            self.init_git_repo(repo)
            (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            self.git(repo, "add", ".gitignore")
            self.git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )
            self.git(repo, "branch", "feature/manual")

            metadata_path = repo / ".worktrees" / "manual.metadata.json"

            with self.assertRaises(SetupError) as ctx:
                setup_worktree(
                    "feature/manual",
                    run_id="manual",
                    no_upstream_metadata=True,
                    cwd=repo,
                )

            self.assertIn("target branch", str(ctx.exception))
            self.assertFalse(metadata_path.exists())

    def test_direct_mode_invalid_branch_ref_fails_without_creating_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            self.init_git_repo(repo)
            (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            self.git(repo, "add", ".gitignore")
            self.git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )

            metadata_path = repo / ".worktrees" / "manual.metadata.json"
            target_worktree = repo / ".worktrees" / "feature..bad"

            with self.assertRaises(SetupError) as ctx:
                setup_worktree(
                    "feature..bad",
                    run_id="manual",
                    no_upstream_metadata=True,
                    cwd=repo,
                )

            self.assertIn("feature..bad", str(ctx.exception))
            self.assertIn("branch", str(ctx.exception))
            self.assertFalse(metadata_path.exists())
            self.assertFalse(target_worktree.exists())

    def test_direct_mode_rejects_empty_ignored_worktrees_directory_without_creating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            (worktrees / "stale-empty-dir").mkdir()
            metadata_path = worktrees / "manual.metadata.json"
            target_worktree = worktrees / "feature" / "manual"
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["status", "--porcelain=v1", "--untracked-files=no"]:
                    return ""
                if args == ["ls-files", "--others", "--exclude-standard"]:
                    return ""
                if args == ["ls-files", "--others", "--ignored", "--exclude-standard"]:
                    return ""
                if args == ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory"]:
                    return ".worktrees/\n"
                if args == ["branch", "--show-current"]:
                    return "main"
                if args == ["rev-parse", "--verify", "HEAD"]:
                    return VALID_SHA
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    Path(args[2]).mkdir(parents=True)
                    return ""
                raise AssertionError(f"unexpected git call: {args!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ):
                with self.assertRaises(SetupError) as ctx:
                    setup_worktree(
                        "feature/manual",
                        run_id="manual",
                        no_upstream_metadata=True,
                        cwd=repo,
                    )

            self.assertIn("Direct-entry metadata creation cannot safely record", str(ctx.exception))
            self.assertFalse(add_called["value"])
            self.assertFalse(metadata_path.exists())
            self.assertFalse(target_worktree.exists())

    def test_direct_mode_rejects_empty_ignored_directory_outside_worktrees_before_creating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            self.init_git_repo(repo)
            (repo / ".gitignore").write_text(".worktrees/\nbuild/\n", encoding="utf-8")
            self.git(repo, "add", ".gitignore")
            self.git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )
            (repo / "build").mkdir()

            metadata_path = repo / ".worktrees" / "manual.metadata.json"
            target_worktree = repo / ".worktrees" / "feature" / "manual"

            with self.assertRaises(SetupError) as ctx:
                setup_worktree(
                    "feature/manual",
                    run_id="manual",
                    no_upstream_metadata=True,
                    cwd=repo,
                )

            self.assertIn("Direct-entry metadata creation cannot safely record", str(ctx.exception))
            self.assertFalse(metadata_path.exists())
            self.assertFalse(target_worktree.exists())

    def test_direct_mode_rejects_empty_untracked_directory_outside_worktrees_before_creating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            self.init_git_repo(repo)
            (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            self.git(repo, "add", ".gitignore")
            self.git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )
            (repo / "scratch").mkdir()

            metadata_path = repo / ".worktrees" / "manual.metadata.json"
            target_worktree = repo / ".worktrees" / "feature" / "manual"

            with self.assertRaises(SetupError) as ctx:
                setup_worktree(
                    "feature/manual",
                    run_id="manual",
                    no_upstream_metadata=True,
                    cwd=repo,
                )

            self.assertIn("Direct-entry metadata creation cannot safely record", str(ctx.exception))
            self.assertFalse(metadata_path.exists())
            self.assertFalse(target_worktree.exists())

    def test_empty_directory_scan_reports_unsafe_nested_directory_without_descending(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            unsafe_dir = repo / "safe" / "unsafe"
            unsafe_dir.mkdir(parents=True)
            (unsafe_dir / "external.txt").write_text("must not be inspected\n", encoding="utf-8")
            worktrees.mkdir()
            checked_paths = []
            real_iterdir = type(repo).iterdir

            def reject_unsafe_nested_directory(path, label, allow_missing=False):
                path = Path(path)
                checked_paths.append(path)
                if path == unsafe_dir:
                    raise PathSafetyError("unsafe nested directory")
                try:
                    return path.lstat()
                except FileNotFoundError:
                    if allow_missing:
                        return None
                    raise

            def guarded_iterdir(path):
                path = Path(path)
                if path == unsafe_dir:
                    raise AssertionError("unsafe nested directory should not be scanned")
                return real_iterdir(path)

            with patch(
                "scripts.double_sdd.setup_worktree.reject_link_or_reparse",
                side_effect=reject_unsafe_nested_directory,
            ), patch.object(type(repo), "iterdir", guarded_iterdir):
                blocking = _blocking_empty_directories(repo, worktrees)

            self.assertEqual(blocking, ["safe/unsafe"])
            self.assertIn(unsafe_dir, checked_paths)

    def test_direct_mode_allows_completed_or_abandoned_top_level_retained_metadata(self):
        for status in ("completed", "abandoned"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp).resolve()
                worktrees = repo / ".worktrees"
                worktrees.mkdir()
                retained = valid_metadata("retained")
                retained["status"] = status
                retained_path = worktrees / "retained.metadata.json"
                retained_path.write_text(json.dumps(retained) + "\n", encoding="utf-8")
                target_metadata_path = worktrees / "manual.metadata.json"
                add_called = {"value": False}

                def fake_run_git(args, cwd):
                    if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                        return str(repo / ".git")
                    if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                        return str(repo / ".git")
                    if args == ["rev-parse", "--show-toplevel"]:
                        return str(repo)
                    if args == ["status", "--porcelain=v1", "--untracked-files=no"]:
                        return ""
                    if args == ["ls-files", "--others", "--exclude-standard"]:
                        return ""
                    if args == ["ls-files", "--others", "--ignored", "--exclude-standard"]:
                        return ".worktrees/retained.metadata.json\n"
                    if args == ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory"]:
                        return ".worktrees/\n"
                    if args == ["branch", "--show-current"]:
                        return "main"
                    if args == ["rev-parse", "--verify", "HEAD"]:
                        return VALID_SHA
                    if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                        return VALID_SHA
                    if len(args) == 6 and args[:2] == ["worktree", "add"]:
                        add_called["value"] = True
                        Path(args[2]).mkdir(parents=True)
                        return ""
                    raise AssertionError(f"unexpected git call: {args!r}")

                with patch(
                    "scripts.double_sdd.setup_worktree._run_git",
                    side_effect=fake_run_git,
                ), patch(
                    "scripts.double_sdd.setup_worktree._git_success",
                    side_effect=self.fake_git_success_clean_preflight,
                ):
                    result = setup_worktree(
                        "feature/manual",
                        run_id="manual",
                        no_upstream_metadata=True,
                        cwd=repo,
                    )

                self.assertTrue(add_called["value"])
                self.assertEqual(result["metadataPath"], ".worktrees/manual.metadata.json")
                self.assertTrue(target_metadata_path.exists())
                unchanged_retained = json.loads(retained_path.read_text(encoding="utf-8"))
                self.assertEqual(unchanged_retained["status"], status)

    def test_success_path_outputs_json_and_updates_metadata_after_worktree_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = repo / ".worktrees" / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    before = json.loads(metadata_path.read_text(encoding="utf-8"))
                    self.assertIsNone(before["featureBranch"])
                    self.assertIsNone(before["worktreePath"])
                    add_called["value"] = True
                    self.assertEqual(Path(args[2]), repo / ".worktrees" / "feature" / "test")
                    Path(args[2]).mkdir(parents=True)
                    return ""
                raise AssertionError(f"unexpected git call: {args!r}")

            out = io.StringIO()
            err = io.StringIO()
            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(
                    [
                        "--branch",
                        "feature/test",
                        "--metadata-path",
                        metadata_relpath,
                    ]
                )

            self.assertEqual(code, 0, err.getvalue())
            self.assertTrue(add_called["value"])
            payload = json.loads(out.getvalue())
            self.assertEqual(
                set(payload),
                {"metadataPath", "worktreePath", "featureBranch"},
            )
            self.assertEqual(payload["metadataPath"], metadata_relpath)
            self.assertEqual(payload["featureBranch"], "feature/test")
            self.assertEqual(payload["worktreePath"], ".worktrees/feature/test")

            updated = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["featureBranch"], "feature/test")
            self.assertEqual(updated["worktreePath"], ".worktrees/feature/test")

    def test_existing_branch_and_worktree_matching_run_repairs_metadata_without_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            branch = "feature/test"
            worktrees = repo / ".worktrees"
            worktree_path = worktrees / "feature" / "test"
            worktree_path.mkdir(parents=True)
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if args == ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"]:
                    return VALID_SHA
                if (
                    args == ["status", "--porcelain=v1", "--untracked-files=all"]
                    and Path(cwd) == worktree_path
                ):
                    return ""
                if args == ["symbolic-ref", "--quiet", "--short", "HEAD"] and Path(cwd) == worktree_path:
                    return branch
                if args == ["rev-parse", "--verify", "HEAD"] and Path(cwd) == worktree_path:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    raise AssertionError("git worktree add should not run for verified repair")
                raise AssertionError(f"unexpected git call: {args!r} cwd={cwd!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_existing_branch,
            ):
                result = setup_worktree(
                    branch,
                    metadata_path=metadata_relpath,
                    cwd=repo,
                )

            self.assertFalse(add_called["value"])
            self.assertEqual(
                result,
                {
                    "metadataPath": metadata_relpath,
                    "worktreePath": ".worktrees/feature/test",
                    "featureBranch": branch,
                },
            )
            updated = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["featureBranch"], branch)
            self.assertEqual(updated["worktreePath"], ".worktrees/feature/test")

    def test_existing_final_mount_worktree_target_rejects_without_finalizing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            branch = "feature/test"
            worktrees = repo / ".worktrees"
            worktree_path = worktrees / "feature" / "test"
            worktree_path.mkdir(parents=True)
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if args == ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"]:
                    return VALID_SHA
                if (
                    args == ["status", "--porcelain=v1", "--untracked-files=all"]
                    and Path(cwd) == worktree_path
                ):
                    return ""
                if args == ["symbolic-ref", "--quiet", "--short", "HEAD"] and Path(cwd) == worktree_path:
                    return branch
                if args == ["rev-parse", "--verify", "HEAD"] and Path(cwd) == worktree_path:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    raise AssertionError("git worktree add should not run for preexisting targets")
                raise AssertionError(f"unexpected git call: {args!r} cwd={cwd!r}")

            def fake_is_mount_point(path):
                return Path(path) == worktree_path

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_existing_branch,
            ), patch(
                "scripts.double_sdd.setup_worktree.is_mount_point",
                side_effect=fake_is_mount_point,
            ):
                with self.assertRaises(SetupError) as ctx:
                    setup_worktree(
                        branch,
                        metadata_path=metadata_relpath,
                        cwd=repo,
                    )

            self.assertIn("mount point", str(ctx.exception))
            self.assertFalse(add_called["value"])
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_explicit_metadata_path_repair_finalizes_selected_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            branch = "feature/test"
            worktrees = repo / ".worktrees"
            worktree_path = worktrees / "feature" / "test"
            worktree_path.mkdir(parents=True)
            actual_metadata_path = worktrees / "actual.metadata.json"
            selected_metadata_relpath = ".worktrees/selected.metadata.json"
            selected_metadata_path = worktrees / "selected.metadata.json"
            actual_metadata_path.write_text(json.dumps(valid_metadata("actual")) + "\n", encoding="utf-8")
            selected_metadata_path.write_text(json.dumps(valid_metadata("selected")) + "\n", encoding="utf-8")
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if args == ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"]:
                    return VALID_SHA
                if (
                    args == ["status", "--porcelain=v1", "--untracked-files=all"]
                    and Path(cwd) == worktree_path
                ):
                    return ""
                if args == ["symbolic-ref", "--quiet", "--short", "HEAD"] and Path(cwd) == worktree_path:
                    return branch
                if args == ["rev-parse", "--verify", "HEAD"] and Path(cwd) == worktree_path:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    raise AssertionError("git worktree add should not run for preexisting targets")
                raise AssertionError(f"unexpected git call: {args!r} cwd={cwd!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_existing_branch,
            ):
                result = setup_worktree(
                    branch,
                    metadata_path=selected_metadata_relpath,
                    cwd=repo,
                )

            self.assertFalse(add_called["value"])
            self.assertEqual(
                result,
                {
                    "metadataPath": selected_metadata_relpath,
                    "worktreePath": ".worktrees/feature/test",
                    "featureBranch": branch,
                },
            )
            unchanged = json.loads(actual_metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])
            updated = json.loads(selected_metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["featureBranch"], branch)
            self.assertEqual(updated["worktreePath"], ".worktrees/feature/test")

    def test_repair_rejects_unrelated_nested_repo_with_matching_branch_and_head_without_finalizing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            self.init_git_repo(repo)
            (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            (repo / "README.md").write_text("initial\n", encoding="utf-8")
            self.git(repo, "add", ".gitignore", "README.md")
            self.git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )
            main_base = self.git(repo, "rev-parse", "--verify", "HEAD")
            branch = "feature/test"
            self.git(repo, "branch", branch, main_base)

            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            worktree_path = worktrees / "feature" / "test"
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata = valid_metadata("run")
            metadata["mainBase"] = main_base
            metadata_path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")

            self.git(repo, "clone", "--branch", branch, str(repo), str(worktree_path))

            with self.assertRaises(SetupError) as ctx:
                setup_worktree(
                    branch,
                    metadata_path=metadata_relpath,
                    cwd=repo,
                )

            self.assertIn("repository", str(ctx.exception))
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_repair_rejects_dirty_existing_linked_worktree_without_finalizing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            self.init_git_repo(repo)
            (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
            (repo / "README.md").write_text("initial\n", encoding="utf-8")
            self.git(repo, "add", ".gitignore", "README.md")
            self.git(
                repo,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "initial",
            )
            main_base = self.git(repo, "rev-parse", "--verify", "HEAD")
            branch = "feature/test"

            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            worktree_path = worktrees / "feature" / "test"
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata = valid_metadata("run")
            metadata["mainBase"] = main_base
            metadata_path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")

            self.git(repo, "worktree", "add", str(worktree_path), "-b", branch, main_base)
            (worktree_path / "notes.txt").write_text("dirty\n", encoding="utf-8")

            with self.assertRaises(SetupError) as ctx:
                setup_worktree(
                    branch,
                    metadata_path=metadata_relpath,
                    cwd=repo,
                )

            self.assertIn("clean", str(ctx.exception))
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_existing_branch_or_worktree_mismatch_fails_without_finalizing_metadata(self):
        mismatch_sha = "b" * 40
        cases = (
            ("branch-mainbase", mismatch_sha, "feature/test", VALID_SHA, "branch"),
            ("worktree-branch", VALID_SHA, "feature/other", VALID_SHA, "branch"),
            ("worktree-head", VALID_SHA, "feature/test", mismatch_sha, "HEAD"),
        )
        for name, branch_sha, worktree_branch, worktree_head, expected_message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp).resolve()
                branch = "feature/test"
                worktrees = repo / ".worktrees"
                worktree_path = worktrees / "feature" / "test"
                worktree_path.mkdir(parents=True)
                metadata_relpath = ".worktrees/run.metadata.json"
                metadata_path = worktrees / "run.metadata.json"
                metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
                add_called = {"value": False}

                def fake_run_git(args, cwd):
                    if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                        return str(repo / ".git")
                    if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                        return str(repo / ".git")
                    if args == ["rev-parse", "--show-toplevel"]:
                        return str(repo)
                    if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                        return VALID_SHA
                    if args == ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"]:
                        return branch_sha
                    if (
                        args == ["status", "--porcelain=v1", "--untracked-files=all"]
                        and Path(cwd) == worktree_path
                    ):
                        return ""
                    if args == ["symbolic-ref", "--quiet", "--short", "HEAD"] and Path(cwd) == worktree_path:
                        return worktree_branch
                    if args == ["rev-parse", "--verify", "HEAD"] and Path(cwd) == worktree_path:
                        return worktree_head
                    if len(args) == 6 and args[:2] == ["worktree", "add"]:
                        add_called["value"] = True
                        raise AssertionError("git worktree add should not run for repair mismatch")
                    raise AssertionError(f"unexpected git call: {args!r} cwd={cwd!r}")

                with patch(
                    "scripts.double_sdd.setup_worktree._run_git",
                    side_effect=fake_run_git,
                ), patch(
                    "scripts.double_sdd.setup_worktree._git_success",
                    side_effect=self.fake_git_success_existing_branch,
                ):
                    with self.assertRaises(SetupError) as ctx:
                        setup_worktree(
                            branch,
                            metadata_path=metadata_relpath,
                            cwd=repo,
                        )

                self.assertIn(expected_message, str(ctx.exception))
                self.assertFalse(add_called["value"])
                unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertIsNone(unchanged["featureBranch"])
                self.assertIsNone(unchanged["worktreePath"])

    def test_path_escaping_branch_is_rejected_before_worktree_add_and_metadata_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    Path(args[2]).mkdir(parents=True)
                    return ""
                raise AssertionError(f"unexpected git call: {args!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ):
                with self.assertRaises(SetupError):
                    setup_worktree(
                        "feature/../../escape",
                        metadata_path=metadata_relpath,
                        cwd=repo,
                    )

            self.assertFalse(add_called["value"])
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_direct_mode_rejects_windows_reserved_worktree_path_before_metadata_write(self):
        for branch in ("con", "feature/con"):
            with self.subTest(branch=branch), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp).resolve()
                metadata_path = repo / ".worktrees" / "manual.metadata.json"

                def fake_run_git(args, cwd):
                    if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                        return str(repo / ".git")
                    if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                        return str(repo / ".git")
                    if args == ["rev-parse", "--show-toplevel"]:
                        return str(repo)
                    raise AssertionError(f"unexpected git call: {args!r}")

                def fail_if_preflight_runs(args, cwd):
                    raise AssertionError(f"target preflight should not run for unsafe branch path: {args!r}")

                with patch(
                    "scripts.double_sdd.setup_worktree._run_git",
                    side_effect=fake_run_git,
                ), patch(
                    "scripts.double_sdd.setup_worktree._git_success",
                    side_effect=fail_if_preflight_runs,
                ):
                    with self.assertRaises(SetupError) as ctx:
                        setup_worktree(
                            branch,
                            run_id="manual",
                            no_upstream_metadata=True,
                            cwd=repo,
                        )

                self.assertIn("Windows reserved device name", str(ctx.exception))
                self.assertFalse(metadata_path.exists())

    def test_unsafe_intermediate_worktree_ancestor_rejects_before_add_and_metadata_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            unsafe_ancestor = worktrees / "feature"
            unsafe_ancestor.mkdir()
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            add_called = {"value": False}
            checked_paths = []

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    Path(args[2]).mkdir(parents=True)
                    return ""
                raise AssertionError(f"unexpected git call: {args!r}")

            def reject_unsafe_feature_ancestor(path, label, allow_missing=False):
                path = Path(path)
                checked_paths.append(path)
                if path == unsafe_ancestor:
                    raise PathSafetyError("feature ancestor is unsafe")
                try:
                    return path.lstat()
                except FileNotFoundError:
                    if allow_missing:
                        return None
                    raise

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ), patch(
                "scripts.double_sdd.setup_worktree.reject_link_or_reparse",
                side_effect=reject_unsafe_feature_ancestor,
            ):
                with self.assertRaises(SetupError) as ctx:
                    setup_worktree(
                        "feature/test",
                        metadata_path=metadata_relpath,
                        cwd=repo,
                    )

            self.assertIn("feature ancestor is unsafe", str(ctx.exception))
            self.assertIn(unsafe_ancestor, checked_paths)
            self.assertFalse(add_called["value"])
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_regular_file_intermediate_worktree_ancestor_rejects_before_add_and_metadata_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            (worktrees / "feature").write_text("not a directory\n", encoding="utf-8")
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            add_called = {"value": False}

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    add_called["value"] = True
                    raise SetupError("git worktree add should not be invoked")
                raise AssertionError(f"unexpected git call: {args!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ):
                with self.assertRaises(SetupError) as ctx:
                    setup_worktree(
                        "feature/test",
                        metadata_path=metadata_relpath,
                        cwd=repo,
                    )

            self.assertIn("ancestor must be a directory", str(ctx.exception))
            self.assertFalse(add_called["value"])
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_worktree_add_failure_does_not_finalize_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    raise SetupError("simulated worktree add failure")
                raise AssertionError(f"unexpected git call: {args!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ):
                with self.assertRaises(SetupError):
                    setup_worktree(
                        "feature/test",
                        metadata_path=metadata_relpath,
                        cwd=repo,
                    )

            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def test_post_add_metadata_main_base_drift_rejects_without_finalizing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            worktrees = repo / ".worktrees"
            worktrees.mkdir()
            metadata_relpath = ".worktrees/run.metadata.json"
            metadata_path = worktrees / "run.metadata.json"
            metadata_path.write_text(json.dumps(valid_metadata("run")) + "\n", encoding="utf-8")
            drifted_main_base = "b" * 40

            def fake_run_git(args, cwd):
                if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                    return str(repo / ".git")
                if args == ["rev-parse", "--show-toplevel"]:
                    return str(repo)
                if args == ["rev-parse", "--verify", f"{VALID_SHA}^{{commit}}"]:
                    return VALID_SHA
                if len(args) == 6 and args[:2] == ["worktree", "add"]:
                    Path(args[2]).mkdir(parents=True)
                    drifted = json.loads(metadata_path.read_text(encoding="utf-8"))
                    drifted["mainBase"] = drifted_main_base
                    metadata_path.write_text(json.dumps(drifted) + "\n", encoding="utf-8")
                    return ""
                raise AssertionError(f"unexpected git call: {args!r}")

            with patch(
                "scripts.double_sdd.setup_worktree._run_git",
                side_effect=fake_run_git,
            ), patch(
                "scripts.double_sdd.setup_worktree._git_success",
                side_effect=self.fake_git_success_clean_preflight,
            ):
                with self.assertRaises(SetupError) as ctx:
                    setup_worktree(
                        "feature/test",
                        metadata_path=metadata_relpath,
                        cwd=repo,
                    )

            message = str(ctx.exception)
            self.assertIn("git worktree add succeeded but metadata update failed", message)
            self.assertIn("mainBase", message)
            unchanged = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(unchanged["mainBase"], drifted_main_base)
            self.assertIsNone(unchanged["featureBranch"])
            self.assertIsNone(unchanged["worktreePath"])

    def fake_git_for_direct_dirty(self, repo, state):
        def fake_run_git(args, cwd):
            if args == ["rev-parse", "--path-format=absolute", "--git-dir"]:
                return str(repo / ".git")
            if args == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
                return str(repo / ".git")
            if args == ["rev-parse", "--show-toplevel"]:
                return str(repo)
            if args == ["status", "--porcelain=v1", "--untracked-files=no"]:
                return state.get("tracked", "")
            if args == ["ls-files", "--others", "--exclude-standard"]:
                return state.get("untracked", "")
            if args == ["ls-files", "--others", "--ignored", "--exclude-standard"]:
                return state.get("ignored", "")
            if args == ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory"]:
                return state.get("ignored_with_directories", state.get("ignored", ""))
            raise AssertionError(f"unexpected git call: {args!r}")

        return fake_run_git

    def fake_git_success_clean_preflight(self, args, cwd):
        if args[:3] == ["check-ignore", "-q", "--"]:
            return True
        if args[:3] == ["show-ref", "--verify", "--quiet"]:
            return False
        raise AssertionError(f"unexpected git success call: {args!r}")

    def fake_git_success_existing_branch(self, args, cwd):
        if args[:3] == ["check-ignore", "-q", "--"]:
            return True
        if args[:3] == ["show-ref", "--verify", "--quiet"]:
            return True
        raise AssertionError(f"unexpected git success call: {args!r}")

    def init_git_repo(self, repo):
        self.git(repo, "init", "-b", "main")

    def git(self, repo, *args):
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
        return result.stdout.strip()
