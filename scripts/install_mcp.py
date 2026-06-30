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
from user_context import UserContext, detect_user_context  # noqa: E402

MCP_KEY = "z2h-explore"
REQUIRED_FILES = ("server.py", "api.py", "requirements.txt")


def resolve_install_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_dir = os.getenv("Z2H_EXPLORE_MCP_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.home() / "z2h-explore-mcp"


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


def clone_repo(repo_url: str, target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        if all((target / name).exists() for name in REQUIRED_FILES):
            print(f"Using existing install at {target}")
            return
        raise SystemExit(f"Install dir exists but is not a z2h-explore-mcp repo: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
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
        return bundled
    if all((install_dir / name).exists() for name in REQUIRED_FILES):
        return install_dir
    if repo_url:
        clone_repo(repo_url, install_dir)
        return install_dir
    if tarball_url:
        download_tarball(tarball_url, install_dir)
        return install_dir
    if bundled:
        copy_bundled_repo(bundled, install_dir)
        return install_dir
    raise SystemExit(
        "Could not find z2h-explore-mcp sources.\n"
        "Set Z2H_EXPLORE_MCP_REPO (git URL) or Z2H_EXPLORE_MCP_TARBALL_URL,\n"
        "or run this script from inside the unzipped repo folder."
    )


def setup_venv(install_dir: Path) -> Path:
    venv_dir = install_dir / "venv"
    python_bin = venv_dir / "bin" / "python3"
    if not python_bin.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])
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


def merge_mcp_json(install_dir: Path, mcp_json_path: Path, python_bin: Path, ctx: UserContext) -> None:
    entry = ctx.mcp_json_entry(install_dir, python_bin)
    mcp_json_path.parent.mkdir(parents=True, exist_ok=True)
    if mcp_json_path.exists():
        try:
            config = json.loads(mcp_json_path.read_text())
        except json.JSONDecodeError:
            backup = mcp_json_path.with_suffix(".json.bak")
            shutil.copy2(mcp_json_path, backup)
            print(f"Backed up invalid mcp.json to {backup}")
            config = {}
    else:
        config = {}
    if not isinstance(config, dict):
        config = {}
    if "mcpServers" in config and isinstance(config["mcpServers"], dict):
        servers = config["mcpServers"]
    else:
        servers = {k: v for k, v in config.items() if k != "mcpServers" and isinstance(v, dict)}
        config = {"mcpServers": servers}
    servers[MCP_KEY] = entry
    mcp_json_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Updated {mcp_json_path} (added/updated '{MCP_KEY}')")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Install z2h-explore MCP (any install path)")
    parser.add_argument(
        "--dir",
        dest="install_dir",
        help="Install folder (default: ~/z2h-explore-mcp or $Z2H_EXPLORE_MCP_DIR)",
    )
    parser.add_argument("--repo-url", default=os.getenv("Z2H_EXPLORE_MCP_REPO"), help="Git clone URL")
    parser.add_argument(
        "--tarball-url",
        default=os.getenv("Z2H_EXPLORE_MCP_TARBALL_URL"),
        help="Tarball URL if not using git",
    )
    parser.add_argument("--skip-mcp-json", action="store_true", help="Do not edit ~/.cursor/mcp.json")
    args = parser.parse_args()

    install_dir = resolve_install_dir(args.install_dir)
    print(f"Install dir: {install_dir}")

    install_dir = ensure_repo(install_dir, args.repo_url, args.tarball_url)
    python_bin = setup_venv(install_dir)

    ctx = context_for_install(install_dir)
    write_env_file(install_dir, ctx)

    if not args.skip_mcp_json:
        merge_mcp_json(install_dir, ctx.cursor_mcp_json, python_bin, ctx)

    prompt_path = write_personalized_prompt(install_dir)
    ctx = context_for_install(install_dir)

    print("\nDone.")
    print(f"  Installed to: {install_dir}")
    print(f"  Detected: {ctx.display_name} ({ctx.account_slug})")
    if not args.skip_mcp_json:
        print(f"  Cursor config: {ctx.cursor_mcp_json}")
        print("  Restart Cursor to load z2h-explore.")
    print(f"  Optional follow-up prompt: {prompt_path}")
    print("\nTry in Cursor after restart:")
    print('  "list explores in campaign-explore"')


if __name__ == "__main__":
    main()
