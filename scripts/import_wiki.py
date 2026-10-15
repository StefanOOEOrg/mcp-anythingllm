"""One-time import of a folder of Markdown notes into AnythingLLM workspaces.

    venv/bin/python scripts/import_wiki.py CORPUS [--default Personal]
        [--folder Work=Work ...] [--strip Notes ...] [--dry-run]

Files below a folder named in --folder go to that workspace, everything else to --default.
Missing workspaces are created. Imported files are remembered in a state file, so a rerun
only adds what is new. Needs ANYTHINGLLM_URL / ANYTHINGLLM_API_KEY (environment or .env).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client import Client  # pylint: disable=wrong-import-position

STATE = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local/state")) / "anythingllm-import.json"


def workspace_for(rel: Path, folders: dict[str, str], default: str) -> str:
    """Name of the workspace a corpus file belongs to (first matching folder wins)."""
    return next((space for folder, space in folders.items() if folder in rel.parts), default)


def title_for(rel: Path, strip: set[str]) -> str:
    """'Notes/Sport/Bike.md' with strip {'Notes'} → 'Sport/Bike' (readable source name)."""
    return "/".join(p for p in rel.with_suffix("").parts if p not in strip)


def corpus_files(root: Path) -> list[Path]:
    """All Markdown files below root, without hidden folders (.obsidian, .git …)."""
    return sorted(p for p in root.rglob("*.md")
                  if not any(part.startswith(".") for part in p.relative_to(root).parts))


def parse_args() -> argparse.Namespace:
    """Command line; --folder FOLDER=WORKSPACE may be repeated."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--default", default="Personal", help="workspace for all other files")
    parser.add_argument("--folder", action="append", default=[], metavar="FOLDER=WORKSPACE")
    parser.add_argument("--strip", action="append", default=[], metavar="FOLDER",
                        help="folder names left out of document titles")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    args.folders = dict(item.split("=", 1) for item in args.folder)
    return args


def main() -> int:
    """Import every file not imported yet; print one line per file."""
    args = parse_args()
    client = Client()
    done = set(json.loads(STATE.read_text())) if STATE.exists() else set()
    # name → slug; AnythingLLM drops non-ASCII letters from slugs ("Café" → "caf")
    slugs = {w["name"]: w["slug"] for w in client.workspaces()}
    for name in {args.default, *args.folders.values()} - slugs.keys():
        slug = client.create_workspace(name).get("slug") if not args.dry_run else name.lower()
        slugs[name] = slug
        print(f"workspace {name} → {slug}")
    for path in corpus_files(args.corpus):
        rel = path.relative_to(args.corpus)
        if str(rel) in done:
            continue
        slug = slugs[workspace_for(rel, args.folders, args.default)]
        print(f"{slug:12} {rel}", flush=True)
        if args.dry_run:
            continue
        client.add_text(slug, title_for(rel, set(args.strip)), path.read_text(encoding="utf-8"),
                        source=f"wiki:{rel}")
        done.add(str(rel))
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(sorted(done), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
