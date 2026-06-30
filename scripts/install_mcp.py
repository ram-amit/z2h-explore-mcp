#!/usr/bin/env python3
"""One-shot installer: fetch repo (if needed), venv, mcp.json, personalized prompt."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from personalize_prompt import DEFAULT_OUTPUT, TEMPLATES, render_template  # noqa: E402
from presets import get_preset  # noqa: E402
from repo_config import (  # noqa: E402
    DEFAULT_INSTALL_DIRNAME,
    DEFAULT_REPO_HTTPS,
    DEFAULT_REPO_SSH,
    GITHUB_WEB_URL,
)
from user_context import UserContext, detect_user_context  # noqa: E402
from mcp_config import (  # noqa: E402
    MCP_KEY,
    claude_code_config_path,
    claude_desktop_config_path,
    merge_mcp_server_config,
)
REQUIRED_FILES = ("server.py", "api.py", "requirements.txt")
MIN_PYTHON = (3, 10)


def python_version_tuple(exe: str) -> tuple[int, int] | None:
    try:
        result = subprocess.run(
            [exe, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            capture_output=True,
            text=True,
            check=True,
        )
        major, minor = result.stdout.strip().split(".", 1)
        return int(major), int(minor)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def python_is_supported(exe: str) -> bool:
    version = python_version_tuple(exe)
    return version is not None and version >= MIN_PYTHON


def python_candidates() -> list[str]:
    names = [
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
    ]
    brew_roots = ["/opt/homebrew", "/usr/local"]
    for root in brew_roots:
        for minor in ("3.13", "3.12", "3.11", "3.10"):
            names.append(f"{root}/opt/python@{minor}/bin/python3")
        names.append(f"{root}/bin/python3")

    seen: set[str] = set()
    candidates: list[str] = []
    for name in names:
        path = shutil.which(name) if "/" not in name else (name if Path(name).exists() else None)
        if not path or path in seen:
            continue
        seen.add(path)
        candidates.append(path)
    return candidates


def find_python(explicit: str | None = None) -> str:
    override = explicit or os.getenv("Z2H_EXPLORE_PYTHON")
    if override:
        if not python_is_supported(override):
            version = python_version_tuple(override)
            label = ".".join(map(str, version)) if version else "unknown"
            raise SystemExit(
                f"Python {label} at {override} is too old. z2h-explore-mcp requires Python 3.10+."
            )
        return override

    for candidate in python_candidates():
        if python_is_supported(candidate):
            version = python_version_tuple(candidate)
            label = ".".join(map(str, version)) if version else candidate
            print(f"Using Python {label}: {candidate}")
            return candidate

    raise SystemExit(
        "Python 3.10+ is required but not found.\n"
        "Install one of:\n"
        "  brew install python@3.12\n"
        "  brew install python\n"
        "Then re-run the installer, or set Z2H_EXPLORE_PYTHON to the new python path."
    )


def default_install_dir() -> Path:
    env_dir = os.getenv("Z2H_EXPLORE_MCP_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.home() / DEFAULT_INSTALL_DIRNAME


def resolve_install_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return default_install_dir()


def find_bundled_repo() -> Path | None:
    candidates = [
        SCRIPT_DIR.parent,
        Path(__file__).resolve().parent.parent,
    ]
    for path in candidates:
        if all((path / name).exists() for name in REQUIRED_FILES):
            return path.resolve()
    return None


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def refresh_git_repo(install_dir: Path) -> None:
    if not (install_dir / ".git").exists():
        return
    print(f"Updating existing clone at {install_dir}")
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=install_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return
    combined = f"{result.stdout}\n{result.stderr}"
    if "would be overwritten by merge" in combined or "local changes" in combined.lower():
        print("Local git changes blocked pull; resetting to origin/main ...")
        subprocess.run(["git", "fetch", "origin"], cwd=install_dir, check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=install_dir, check=True)
        return
    print(combined, file=sys.stderr)
    raise SystemExit(f"git pull failed in {install_dir}")


def clone_repo(repo_url: str, target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        if all((target / name).exists() for name in REQUIRED_FILES):
            refresh_git_repo(target)
            print(f"Using existing install at {target}")
            return
        raise SystemExit(f"Install dir exists but is not a z2h-explore-mcp repo: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning {repo_url} -> {target}")
    run(["git", "clone", repo_url, str(target)])


def download_tarball(url: str, target: Path) -> None:
    if target.exists() and all((target / name).exists() for name in REQUIRED_FILES):
        print(f"Using existing install at {target}")
        return
    print(f"Downloading {url}")
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "archive.tgz"
        urllib.request.urlretrieve(url, archive_path)
        extract_root = Path(tmp) / "extract"
        extract_root.mkdir()
        with tarfile.open(archive_path) as tar:
            tar.extractall(extract_root)
        children = [p for p in extract_root.iterdir() if p.name not in {".DS_Store"}]
        source = children[0] if len(children) == 1 and children[0].is_dir() else extract_root
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)


def copy_bundled_repo(source: Path, target: Path) -> None:
    if target.resolve() == source.resolve():
        return
    if target.exists():
        if all((target / name).exists() for name in REQUIRED_FILES):
            print(f"Using existing install at {target}")
            return
        raise SystemExit(f"Install dir exists but is not a z2h-explore-mcp repo: {target}")
    print(f"Copying bundled repo from {source} -> {target}")
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("venv", ".git", "__pycache__", "*.pyc", ".env"),
    )


def ensure_repo(install_dir: Path, repo_url: str | None, tarball_url: str | None) -> Path:
    bundled = find_bundled_repo()
    if bundled and install_dir.resolve() == bundled.resolve():
        refresh_git_repo(bundled)
        return bundled
    if all((install_dir / name).exists() for name in REQUIRED_FILES):
        refresh_git_repo(install_dir)
        return install_dir
    effective_repo_url = repo_url or os.getenv("Z2H_EXPLORE_MCP_REPO") or DEFAULT_REPO_HTTPS
    if effective_repo_url:
        clone_repo(effective_repo_url, install_dir)
        return install_dir
    if tarball_url:
        download_tarball(tarball_url, install_dir)
        return install_dir
    if bundled:
        copy_bundled_repo(bundled, install_dir)
        return install_dir
    raise SystemExit(
        "Could not find z2h-explore-mcp sources.\n"
        f"Clone {GITHUB_WEB_URL} or run the install script from the repo."
    )


def setup_venv(install_dir: Path, python_exe: str | None = None) -> Path:
    python_exe = find_python(python_exe)
    venv_dir = install_dir / "venv"
    python_bin = venv_dir / "bin" / "python3"
    if python_bin.exists() and not python_is_supported(str(python_bin)):
        print(f"Removing existing venv (Python < 3.10): {venv_dir}")
        shutil.rmtree(venv_dir)
        python_bin = venv_dir / "bin" / "python3"
    if not python_bin.exists():
        run([python_exe, "-m", "venv", str(venv_dir)])
    run([str(python_bin), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python_bin), "-m", "pip", "install", "-r", "requirements.txt"], cwd=install_dir)
    return python_bin


def write_env_file(install_dir: Path, ctx: UserContext) -> Path:
    env_path = install_dir / ".env"
    lines = [
        f"Z2H_EXPLORE_PERSONAL_FOLDER={ctx.campaign_explore_personal_folder}",
        "Z2H_EXPLORE_DEFAULT_STORAGE=personal",
        "",
    ]
    env_path.write_text("\n".join(lines))
    print(f"Wrote {env_path} (personal folder: {ctx.campaign_explore_personal_folder})")
    return env_path


def expand_client_targets(clients: str) -> set[str]:
    mapping = {
        "none": set(),
        "cursor": {"cursor"},
        "claude-code": {"claude-code"},
        "claude-desktop": {"claude-desktop"},
        "claude": {"claude-code", "claude-desktop"},
        "both": {"cursor", "claude-code", "claude-desktop"},
        "all": {"cursor", "claude-code", "claude-desktop"},
    }
    if clients not in mapping:
        raise SystemExit(f"Unknown --clients value: {clients}")
    return mapping[clients]


def configure_clients(
    clients: str,
    install_dir: Path,
    python_bin: Path,
    ctx: UserContext,
) -> list[str]:
    entry = ctx.mcp_json_entry(install_dir, python_bin)
    targets = expand_client_targets(clients)
    updated: list[str] = []

    if "cursor" in targets:
        merge_mcp_server_config(ctx.cursor_mcp_json, entry, label="Cursor")
        updated.append("Cursor")

    if "claude-code" in targets:
        merge_mcp_server_config(
            claude_code_config_path(ctx.home),
            entry,
            label="Claude Code",
        )
        updated.append("Claude Code")

    if "claude-desktop" in targets:
        claude_path = claude_desktop_config_path(ctx.home)
        if claude_path is None:
            print("Claude Desktop config path not detected on this OS; skipping.")
        else:
            merge_mcp_server_config(claude_path, entry, label="Claude Desktop")
            updated.append("Claude Desktop")

    return updated


def print_next_steps(clients: list[str], ctx: UserContext, install_dir: Path) -> None:
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"Install:        {install_dir}")
    print(f"Personal folder: {ctx.campaign_explore_personal_folder}")
    if clients:
        print(f"MCP wired for:  {', '.join(clients)}")
    else:
        print("MCP config:     skipped (venv + .env only)")

    print("\nNext steps:")
    step = 1
    if "Cursor" in clients:
        print(f"  {step}. Quit Cursor fully (Cmd+Q), reopen")
        step += 1
        print(f"  {step}. Cursor → Settings → MCP → confirm '{MCP_KEY}' is connected")
        step += 1
    if "Claude Code" in clients:
        print(f"  {step}. Restart Claude Code (exit terminal session, run `claude` again)")
        step += 1
        print(f"  {step}. In Claude Code, run `/mcp` and confirm '{MCP_KEY}' is listed")
        step += 1
    if "Claude Desktop" in clients:
        print(f"  {step}. Quit Claude Desktop fully (Cmd+Q), reopen")
        step += 1

    print(f"  {step}. In a NEW chat (not monday browser Claude), ask:")
    print('       list explores in campaign-explore')
    print(f"  {step + 1}. Verify: {', '.join(['Campaign Monitoring', 'Advanced Analytics', 'LinkedIn Habu'])}")
    print("\nHealth check anytime:")
    print(f"  cd {install_dir} && python3 scripts/verify_install.py")
    print("\nNote: looker-toolbox is Looker. z2h-explore is campaign-explore on bigbrain.me.")


def preflight(python_exe: str | None) -> None:
    if not _git_config("user.name"):
        print("WARN: git config user.name is not set.")
        print("      Set it so campaign-explore uses the right personal folder:")
        print('      git config --global user.name "First Last"')
    find_python(python_exe)


def _git_config(key: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return value or None


def context_for_install(install_dir: Path) -> UserContext:
    base = detect_user_context()
    return UserContext(
        home=base.home,
        system_username=base.system_username,
        display_name=base.display_name,
        account_slug=base.account_slug,
        development_root=base.development_root,
        z2h_explore_mcp=install_dir,
        cursor_mcp_json=base.cursor_mcp_json,
        git_email=base.git_email,
    )


def write_personalized_prompt(install_dir: Path) -> Path:
    ctx = context_for_install(install_dir)
    preset = get_preset("setup")
    template = TEMPLATES["setup"].read_text()
    output = install_dir / "CURSOR_SETUP_PROMPT.md"
    output.write_text(render_template(ctx, preset, template))
    DEFAULT_OUTPUT.write_text(output.read_text())
    return output


def resolve_clients(args: argparse.Namespace) -> str:
    if args.skip_mcp_json:
        return "none"
    return args.clients


def main() -> None:
    parser = argparse.ArgumentParser(description="Install z2h-explore MCP (any install path)")
    parser.add_argument(
        "--dir",
        dest="install_dir",
        help="Install folder (default: ~/z2h-explore-mcp or $Z2H_EXPLORE_MCP_DIR)",
    )
    parser.add_argument(
        "--repo-url",
        default=os.getenv("Z2H_EXPLORE_MCP_REPO", DEFAULT_REPO_HTTPS),
        help=f"Git clone URL (default: {DEFAULT_REPO_HTTPS})",
    )
    parser.add_argument(
        "--tarball-url",
        default=os.getenv("Z2H_EXPLORE_MCP_TARBALL_URL"),
        help="Tarball URL if not using git",
    )
    parser.add_argument(
        "--clients",
        choices=["cursor", "claude-code", "claude-desktop", "claude", "both", "all", "none"],
        default="cursor",
        help=(
            "Wire MCP config: cursor (default), claude-code (terminal), "
            "claude-desktop (app), claude (both Claude products), both/all (everything)"
        ),
    )
    parser.add_argument(
        "--skip-mcp-json",
        action="store_true",
        help="Deprecated: same as --clients none",
    )
    parser.add_argument(
        "--python",
        default=os.getenv("Z2H_EXPLORE_PYTHON"),
        help="Python 3.10+ executable for venv (default: auto-detect)",
    )
    args = parser.parse_args()

    install_dir = resolve_install_dir(args.install_dir)
    print(f"Install dir: {install_dir}")

    preflight(args.python)
    install_dir = ensure_repo(install_dir, args.repo_url, args.tarball_url)
    python_bin = setup_venv(install_dir, args.python)

    ctx = context_for_install(install_dir)
    write_env_file(install_dir, ctx)

    clients_mode = resolve_clients(args)
    configured = []
    if clients_mode != "none":
        configured = configure_clients(clients_mode, install_dir, python_bin, ctx)

    write_personalized_prompt(install_dir)
    print_next_steps(configured, ctx, install_dir)


if __name__ == "__main__":
    main()
