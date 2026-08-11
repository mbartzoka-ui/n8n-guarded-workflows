#!/usr/bin/env python3
"""Structural checks for the workflows in this repository.

Every workflow here shares one spine — fetch, reason, verify deterministically,
gate on a human, and keep publication switched off — so it is worth checking
that spine mechanically rather than by eye.

The check that earns its keep is `unconnected outputs`. A router with a branch
that goes nowhere silently discards whatever lands in it: the item is not
labelled, nobody is notified, no draft appears. It looks like a quiet day rather
than a bug. That is exactly the defect this script exists to catch, and it was
found by eye in a real workflow before it was ever written down here.

    python validate.py            # check every *.json in this directory
    python validate.py a.json     # check specific files
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Nodes whose unused outputs are legitimately left open.
TERMINAL = {"n8n-nodes-base.noOp"}

# Sub-nodes attach upward into a parent; they have no main output of their own.
SUBNODE_PORTS = ("ai_languageModel", "ai_memory", "ai_tool", "ai_outputParser")

SECRET_HINTS = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}", re.I),          # OpenAI-style keys
    re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}", re.I),      # Anthropic keys
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),                  # GitHub tokens
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r'"(accessToken|apiKey|password|clientSecret)"\s*:\s*"[^"]{8,}"', re.I),
)

# A real address in a public repository is an invitation to scrapers.
REAL_EMAIL = re.compile(r"\b[\w.+-]+@(?!example\.com)[\w-]+\.[\w.]{2,}\b")


def problems_for(path: Path) -> list[str]:
    out: list[str] = []
    raw = path.read_text(encoding="utf-8")

    try:
        wf = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    nodes = wf.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["no nodes array"]

    names: list[str] = []
    for i, node in enumerate(nodes):
        where = node.get("name") or f"node #{i}"
        for field in ("name", "type", "typeVersion", "position", "parameters"):
            if field not in node:
                out.append(f"{where}: missing {field!r}")
        if "name" in node:
            names.append(node["name"])
        pos = node.get("position")
        if not (isinstance(pos, list) and len(pos) == 2):
            out.append(f"{where}: position must be [x, y]")

    duplicates = {n for n in names if names.count(n) > 1}
    for dupe in sorted(duplicates):
        out.append(f"duplicate node name {dupe!r} — connections address nodes by name")

    known = set(names)
    connections = wf.get("connections", {})
    if not isinstance(connections, dict):
        return out + ["connections must be an object"]

    # Sources and targets must both exist.
    reached: set[str] = set()
    for source, ports in connections.items():
        if source not in known:
            out.append(f"connection from unknown node {source!r}")
        for port, groups in (ports or {}).items():
            for group in groups or []:
                for target in group or []:
                    name = target.get("node")
                    if name not in known:
                        out.append(f"{source!r} -> unknown node {name!r}")
                    else:
                        reached.add(name)

    # Every node must be reachable, except the ones that start a run.
    starters = {
        n["name"] for n in nodes
        if "trigger" in n.get("type", "").lower()
        or any(p in connections.get(n.get("name", ""), {}) for p in SUBNODE_PORTS)
    }
    for name in known - reached - starters:
        out.append(f"{name!r} is never reached and is not a trigger or sub-node")

    # THE important one: a declared output that goes nowhere.
    for node in nodes:
        name, ntype = node.get("name"), node.get("type", "")
        if ntype in TERMINAL or node.get("disabled"):
            continue
        if any(p in connections.get(name, {}) for p in SUBNODE_PORTS):
            continue
        groups = (connections.get(name) or {}).get("main")
        if groups is None:
            continue  # a genuine leaf; flagged by the reachability rule if wrong
        for index, group in enumerate(groups):
            if not group:
                out.append(
                    f"{name!r} output #{index} is declared but connected to nothing "
                    f"— items routed there vanish silently"
                )

    # Embedded JavaScript, if node is available to check it. A Code node with a
    # syntax error fails at run time, on the day it matters, inside a scheduled
    # job nobody is watching.
    if shutil.which("node"):
        for n in nodes:
            code = (n.get("parameters") or {}).get("jsCode")
            if not code:
                continue
            # n8n runs a Code node as a function body, so wrap it before parsing.
            with tempfile.NamedTemporaryFile(
                "w", suffix=".js", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write("(async function(){\n" + code + "\n})")
                tmp_path = tmp.name
            result = subprocess.run(
                ["node", "--check", tmp_path], capture_output=True, text=True
            )
            Path(tmp_path).unlink(missing_ok=True)
            if result.returncode != 0:
                detail = (result.stderr or "").strip().splitlines()
                out.append(
                    f"{n.get('name')!r}: jsCode has a syntax error — "
                    f"{detail[-1] if detail else 'see node --check'}"
                )

    for pattern in SECRET_HINTS:
        if pattern.search(raw):
            out.append("looks like it contains a credential or token")
            break

    for match in REAL_EMAIL.finditer(raw):
        address = match.group(0)
        if "@n8n/" in address or address.startswith("@"):
            continue
        out.append(f"real email address {address!r} — use a placeholder instead")

    return out


def main(argv: list[str]) -> int:
    here = Path(__file__).parent
    targets = [Path(a) for a in argv[1:]] or sorted(here.glob("*.json"))
    if not targets:
        print("no workflow files found")
        return 1

    failed = 0
    for path in targets:
        issues = problems_for(path)
        if issues:
            failed += 1
            print(f"FAIL  {path.name}")
            for issue in issues:
                print(f"        {issue}")
        else:
            node_count = len(json.loads(path.read_text(encoding="utf-8"))["nodes"])
            print(f"ok    {path.name}  ({node_count} nodes)")

    print()
    print(f"{len(targets) - failed}/{len(targets)} workflows passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
