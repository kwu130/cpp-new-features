"""Regression checks for feature-gated stacktrace verification."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_examples as verifier


class StacktraceLinkTests(unittest.TestCase):
    def setUp(self):
        verifier.stacktrace_link_flags.cache_clear()
        self.example = verifier.Example(
            identifier="stacktrace-test", standard="c++23", kind="single",
            compilers="all", source=Path("example.md"), line=1,
            files={"main.cpp": "int main() {}\n"},
            requires="__cpp_lib_stacktrace>=202011",
        )

    def result(self, stdout="", code=0):
        return subprocess.CompletedProcess([], code, stdout, "")

    def test_clang_with_libstdcxx_links_archive_after_source(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "libstdc++exp.a"
            archive.touch()
            with patch.object(verifier, "compiler_family", return_value="clang"), \
                    patch.object(verifier, "supports_feature", return_value=True), \
                    patch.object(verifier, "run_command", side_effect=[
                        self.result("CPP_DOC_LIBSTDCXX\n"),
                        self.result(str(archive) + "\n"),
                        self.result(), self.result(),
                    ]) as run:
                self.assertEqual(verifier.verify_one(self.example, "clang++"), "passed")
                command = run.call_args_list[2].args[0]
                self.assertGreater(command.index(str(archive)), command.index("main.cpp"))
                self.assertIn("-std=c++23", command)
                self.assertIn("-pedantic", command)

    def test_older_libstdcxx_uses_backtrace_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "libstdc++_libbacktrace.a"
            archive.touch()
            with patch.object(verifier, "run_command", side_effect=[
                self.result("CPP_DOC_LIBSTDCXX\n"), self.result("libstdc++exp.a\n"),
                self.result(str(archive) + "\n"),
            ]):
                self.assertEqual(verifier.stacktrace_link_flags("g++", "c++23"), (str(archive),))

    def test_libcxx_does_not_link_gnu_support_libraries(self):
        with patch.object(verifier, "run_command", return_value=self.result()) as run:
            self.assertEqual(verifier.stacktrace_link_flags("clang++", "c++23"), ())
            self.assertEqual(run.call_count, 1)

    def test_missing_support_library_fails_instead_of_skipping(self):
        with patch.object(verifier, "run_command", side_effect=[
            self.result("CPP_DOC_LIBSTDCXX\n"), self.result("libstdc++exp.a\n"),
            self.result("libstdc++_libbacktrace.a\n"),
        ]):
            with self.assertRaisesRegex(verifier.VerificationError, "support library was not found"):
                verifier.stacktrace_link_flags("clang++", "c++23")

    def test_probe_failure_is_not_treated_as_another_standard_library(self):
        with patch.object(verifier, "run_command", return_value=self.result(code=1)):
            with self.assertRaisesRegex(verifier.VerificationError, "probe failed"):
                verifier.stacktrace_link_flags("clang++", "c++23")

    def test_unsupported_feature_skips_before_library_lookup(self):
        with patch.object(verifier, "compiler_family", return_value="clang"), \
                patch.object(verifier, "supports_feature", return_value=False), \
                patch.object(verifier, "stacktrace_link_flags") as flags:
            self.assertTrue(verifier.verify_one(self.example, "clang++").startswith("skipped"))
            flags.assert_not_called()

    def test_supported_feature_compile_error_still_fails(self):
        with patch.object(verifier, "compiler_family", return_value="clang"), \
                patch.object(verifier, "supports_feature", return_value=True), \
                patch.object(verifier, "stacktrace_link_flags", return_value=()), \
                patch.object(verifier, "run_command", return_value=self.result(code=1)):
            with self.assertRaisesRegex(verifier.VerificationError, "failed to compile"):
                verifier.verify_one(self.example, "clang++")


if __name__ == "__main__":
    unittest.main()
