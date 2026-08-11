#!/usr/bin/env python3
"""Extract, compile, and run every verified C++ block in the Markdown tree."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


META_RE = re.compile(r'^\s*<!--\s*example\s+(.+?)\s*-->\s*$')
FENCE_RE = re.compile(r'^\s*```(\S*)\s*$')
LINK_RE = re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')
VALID_STANDARDS = {"c++11", "c++14", "c++17", "c++20"}


@dataclass
class Example:
    identifier: str
    standard: str
    kind: str
    compilers: str
    source: Path
    line: int
    output: str | None = None
    files: dict[str, str] = field(default_factory=dict)


class VerificationError(RuntimeError):
    pass


def parse_metadata(raw: str, source: Path, line: int) -> dict[str, str]:
    try:
        tokens = shlex.split(raw)
    except ValueError as error:
        raise VerificationError(f"{source}:{line}: invalid metadata: {error}") from error
    values: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise VerificationError(f"{source}:{line}: invalid metadata token {token!r}")
        key, value = token.split("=", 1)
        if key in values:
            raise VerificationError(f"{source}:{line}: duplicate metadata key {key!r}")
        values[key] = value
    return values


def markdown_files(root: Path, selected: str | None) -> list[Path]:
    files = sorted(root.rglob("*.md"))
    if selected is None:
        return files
    needle = Path(selected)
    return [path for path in files if needle in (path, *path.parents) or selected in str(path)]


def validate_links(root: Path, files: list[Path]) -> None:
    for path in files:
        in_fence = False
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for match in LINK_RE.finditer(line):
                destination = match.group(1).strip()
                if destination.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                relative = destination.split("#", 1)[0]
                target = (path.parent / relative).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError as error:
                    raise VerificationError(f"{path}:{line_number}: link escapes repository: {destination}") from error
                if not target.exists():
                    raise VerificationError(f"{path}:{line_number}: broken relative link: {destination}")


def collect_examples(root: Path, selected: str | None) -> list[Example]:
    groups: dict[str, Example] = {}
    files = markdown_files(root, selected)
    validate_links(root, files)
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        pending: tuple[dict[str, str], int] | None = None
        index = 0
        while index < len(lines):
            meta_match = META_RE.match(lines[index])
            if meta_match:
                pending = (parse_metadata(meta_match.group(1), path, index + 1), index + 1)
                index += 1
                continue
            fence_match = FENCE_RE.match(lines[index])
            if not fence_match:
                if lines[index].strip() and pending is not None:
                    pending = None
                index += 1
                continue
            language = fence_match.group(1)
            fence_line = index + 1
            index += 1
            body: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                body.append(lines[index])
                index += 1
            if index == len(lines):
                raise VerificationError(f"{path}:{fence_line}: unclosed code fence")
            index += 1
            if language != "cpp":
                pending = None
                continue
            if pending is None:
                raise VerificationError(f"{path}:{fence_line}: cpp fence has no adjacent example metadata")
            metadata, meta_line = pending
            pending = None
            required = {"id", "std", "file", "kind", "compilers"}
            missing = sorted(required - metadata.keys())
            if missing:
                raise VerificationError(f"{path}:{meta_line}: missing metadata: {', '.join(missing)}")
            if metadata["std"] not in VALID_STANDARDS:
                raise VerificationError(f"{path}:{meta_line}: unsupported standard {metadata['std']!r}")
            if metadata["compilers"] not in {"all", "gcc", "clang"}:
                raise VerificationError(f"{path}:{meta_line}: invalid compilers value")
            identifier = metadata["id"]
            example = groups.get(identifier)
            if example is None:
                example = Example(
                    identifier=identifier,
                    standard=metadata["std"],
                    kind=metadata["kind"],
                    compilers=metadata["compilers"],
                    source=path,
                    line=meta_line,
                    output=metadata.get("output"),
                )
                groups[identifier] = example
            elif (
                example.standard != metadata["std"]
                or example.kind != metadata["kind"]
                or example.compilers != metadata["compilers"]
                or example.source != path
            ):
                raise VerificationError(f"{path}:{meta_line}: inconsistent or cross-document duplicate ID {identifier!r}")
            filename = metadata["file"]
            if filename in example.files:
                raise VerificationError(f"{path}:{meta_line}: duplicate file {filename!r} in {identifier!r}")
            if ".." in Path(filename).parts or Path(filename).is_absolute():
                raise VerificationError(f"{path}:{meta_line}: unsafe example filename {filename!r}")
            example.files[filename] = "\n".join(body) + "\n"
    if not groups:
        raise VerificationError("no examples matched the requested selection")
    return list(groups.values())


def compiler_family(compiler: str) -> str:
    result = subprocess.run(
        [compiler, "--version"], text=True, capture_output=True, timeout=10, check=False
    )
    identity = (result.stdout + result.stderr).lower()
    return "clang" if "clang" in identity else "gcc"


def run_command(command: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def verify_one(example: Example, compiler: str) -> str:
    family = compiler_family(compiler)
    if example.compilers not in {"all", family}:
        return "skipped"
    with tempfile.TemporaryDirectory(prefix=f"cpp-doc-{example.identifier}-") as directory:
        work = Path(directory)
        for filename, content in example.files.items():
            target = work / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        executable = work / "example"
        common = [compiler, f"-std={example.standard}", "-Wall", "-Wextra", "-pedantic"]
        if example.kind == "single":
            if set(example.files) != {"main.cpp"}:
                raise VerificationError(f"{example.source}:{example.line}: single example must contain main.cpp only")
            command = common + ["main.cpp", "-pthread", "-o", str(executable)]
            result = run_command(command, work)
        elif example.kind == "modules":
            if family != "gcc":
                return "skipped"
            required = {"math.cppm", "main.cpp"}
            if set(example.files) != required:
                raise VerificationError(f"{example.source}:{example.line}: modules example requires math.cppm and main.cpp")
            module = run_command(common + ["-fmodules-ts", "-x", "c++", "-c", "math.cppm", "-o", "math.o"], work)
            if module.returncode != 0:
                result = module
                command = common + ["-fmodules-ts", "-x", "c++", "-c", "math.cppm"]
            else:
                command = common + ["-fmodules-ts", "main.cpp", "math.o", "-o", str(executable)]
                result = run_command(command, work)
        else:
            raise VerificationError(f"{example.source}:{example.line}: unknown kind {example.kind!r}")
        if result.returncode != 0:
            details = result.stdout + result.stderr
            raise VerificationError(
                f"{example.source}:{example.line}: {example.identifier} failed to compile\n"
                f"command: {' '.join(command)}\n{details}"
            )
        try:
            execution = run_command([str(executable)], work, timeout=10)
        except subprocess.TimeoutExpired as error:
            raise VerificationError(f"{example.source}:{example.line}: {example.identifier} timed out") from error
        if execution.returncode != 0:
            raise VerificationError(
                f"{example.source}:{example.line}: {example.identifier} exited with {execution.returncode}\n"
                f"{execution.stdout}{execution.stderr}"
            )
        actual = execution.stdout.rstrip("\n")
        if example.output is not None and actual != example.output:
            raise VerificationError(
                f"{example.source}:{example.line}: {example.identifier} output mismatch\n"
                f"expected: {example.output!r}\nactual: {actual!r}"
            )
    return "passed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="c++", help="compiler executable")
    parser.add_argument("--path", help="only verify Markdown paths containing this value")
    parser.add_argument("--list", action="store_true", help="list examples without compiling")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        examples = collect_examples(root, args.path)
        if args.list:
            for example in examples:
                print(f"{example.identifier}\t{example.standard}\t{example.source.relative_to(root)}")
            return 0
        passed = skipped = 0
        for example in examples:
            status = verify_one(example, args.compiler)
            if status == "passed":
                passed += 1
                print(f"PASS {example.identifier}")
            else:
                skipped += 1
                print(f"SKIP {example.identifier}")
        print(f"verified with {args.compiler}: {passed} passed, {skipped} skipped")
        return 0
    except VerificationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
