#!/usr/bin/env python3
"""Generate a ready-to-paste Cursor prompt (API + tools pre-filled)."""

from __future__ import annotations

import argparse
from pathlib import Path

from presets import get_preset
from user_context import detect_user_context

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "setup": ROOT / "templates" / "INSTALL_Z2H_EXPLORE.template.md",
    "custom": ROOT / "templates" / "PASTE_TO_CREATE_MCP.template.md",
}
DEFAULT_OUTPUT = ROOT / "templates" / "PASTE_TO_CREATE_MCP.md"


def render_template(ctx, preset, template_text: str) -> str:
    mcp_folder = ctx.z2h_explore_mcp if preset.folder_name == "z2h-explore-mcp" else ctx.development_root / preset.folder_name

    replacements = {
        "{{DISPLAY_NAME}}": ctx.display_name,
        "{{ACCOUNT_SLUG}}": ctx.account_slug,
        "{{SYSTEM_USERNAME}}": ctx.system_username,
        "{{HOME}}": str(ctx.home),
        "{{DEVELOPMENT_ROOT}}": str(ctx.development_root),
        "{{Z2H_EXPLORE_MCP_PATH}}": str(ctx.z2h_explore_mcp),
        "{{MCP_JSON_PATH}}": str(ctx.cursor_mcp_json),
        "{{CAMPAIGN_EXPLORE_PERSONAL_FOLDER}}": ctx.campaign_explore_personal_folder,
        "{{MCP_NAME}}": preset.mcp_name,
        "{{MCP_FOLDER}}": str(mcp_folder),
        "{{SYSTEM}}": preset.system,
        "{{API_BASE_URL}}": preset.api_base_url,
        "{{API_PREFIX}}": preset.api_prefix,
        "{{AUTH}}": preset.auth,
        "{{GOAL}}": preset.goal,
        "{{TOOLS_MARKDOWN}}": preset.tools_markdown,
        "{{OUT_OF_SCOPE}}": preset.out_of_scope,
        "{{TASK_SUMMARY}}": preset.task_summary,
    }
    rendered = template_text
    for _ in range(3):
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Slack-ready Cursor prompt with API/tools pre-filled",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(TEMPLATES),
        default="setup",
        help="setup = install z2h-explore (default); custom = build a new MCP from scratch",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output markdown file")
    parser.add_argument("--install-dir", type=Path, default=None, help="Override MCP install folder")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")
    args = parser.parse_args()

    template_path = TEMPLATES[args.preset]
    if not template_path.exists():
        raise SystemExit(f"Template not found: {template_path}")

    install_dir = args.install_dir.expanduser().resolve() if args.install_dir else None
    ctx = detect_user_context(install_dir)
    preset = get_preset(args.preset)
    rendered = render_template(ctx, preset, template_path.read_text())

    if args.stdout:
        print(rendered)
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"Preset: {preset.label}")
    print(f"Detected:\n{ctx.summary()}\n")
    print(f"Wrote -> {args.output}")
    print("Copy that file into Cursor. No API/tools fields to fill.")


if __name__ == "__main__":
    main()
