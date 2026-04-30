"""Tiny server-rendered WebUI for the lazy workspace control plane."""

from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from research_hub.dispatch import (
    approve_proposal,
    create_dispatch_proposal,
    load_proposals,
)
from research_hub.intake import create_intake_item, load_intake_items
from research_hub.registry import WorkspaceRecord, add_workspace, load_registry


def run_web(
    hub_root: Path,
    host: str = "127.0.0.1",
    port: int = 8787,
    token: str = "",
) -> None:
    handler = make_handler(hub_root.resolve(), token)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"http://{host}:{port}/")
    server.serve_forever()


def make_handler(hub_root: Path, token: str) -> type[BaseHTTPRequestHandler]:
    class HubWebHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if not self.is_authorized():
                self.write_response(403, "Forbidden")
                return
            self.write_response(200, render_home(hub_root, self.query_message()))

        def do_POST(self) -> None:
            if not self.is_authorized():
                self.write_response(403, "Forbidden")
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            form = {
                key: values[-1]
                for key, values in parse_qs(raw, keep_blank_values=True).items()
            }
            try:
                message = handle_post(hub_root, self.path, form)
                self.redirect(f"/?message={message}")
            except Exception as exc:  # pragma: no cover - defensive UI surface
                self.write_response(400, render_home(hub_root, str(exc)))

        def log_message(self, format: str, *args: Any) -> None:
            return

        def query_message(self) -> str:
            parsed = urlparse(self.path)
            values = parse_qs(parsed.query).get("message", [])
            return values[-1] if values else ""

        def is_authorized(self) -> bool:
            if not token:
                return True
            parsed = urlparse(self.path)
            query_token = parse_qs(parsed.query).get("token", [""])[-1]
            return query_token == token or self.headers.get("X-Research-Hub-Token") == token

        def redirect(self, target: str) -> None:
            self.send_response(303)
            self.send_header("Location", target)
            self.end_headers()

        def write_response(self, status: int, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return HubWebHandler


def handle_post(hub_root: Path, path: str, form: dict[str, str]) -> str:
    route = urlparse(path).path
    if route == "/registry-add":
        add_workspace(
            hub_root,
            WorkspaceRecord(
                workspace_id=require(form, "workspace_id"),
                machine_role=require(form, "machine_role"),
                storage_role=require(form, "storage_role"),
                root_hint=form.get("root_hint", ""),
                tailnet_hint=form.get("tailnet_hint", ""),
                inbox_path=require(form, "inbox_path"),
                can_store_library_blobs=form.get("can_store_library_blobs") == "on",
                can_run_training=form.get("can_run_training") == "on",
                capabilities=split_capabilities(form.get("capabilities", "")),
                transport=form.get("transport", "local_path") or "local_path",
                ssh_host=form.get("ssh_host", ""),
                ssh_user=form.get("ssh_user", ""),
                remote_inbox=form.get("remote_inbox", ""),
                hub_ssh_host=form.get("hub_ssh_host", ""),
                hub_ssh_user=form.get("hub_ssh_user", ""),
                hub_ssh_root=form.get("hub_ssh_root", ""),
            ),
        )
        return "workspace-added"
    if route == "/intake-add":
        item = create_intake_item(
            hub_root=hub_root,
            source_path=Path(require(form, "source_path")).resolve(),
            title=require(form, "title"),
            kind=form.get("kind", "user_upload") or "user_upload",
        )
        return f"intake-added-{item['item_id']}"
    if route == "/dispatch-propose":
        proposal = create_dispatch_proposal(hub_root, require(form, "item_id"))
        return f"proposal-created-{proposal['proposal_id']}"
    if route == "/dispatch-approve":
        requests = approve_proposal(
            hub_root,
            require(form, "proposal_id"),
            [require(form, "workspace_id")],
        )
        return f"approved-{len(requests)}-request"
    raise ValueError(f"unknown route: {route}")


def require(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing required field: {key}")
    return value


def split_capabilities(value: str) -> list[str]:
    return sorted({part.strip() for part in value.replace(",", " ").split() if part.strip()})


def render_home(hub_root: Path, message: str = "") -> str:
    registry = load_registry(hub_root)
    intake_items = load_intake_items(hub_root)
    proposals = load_proposals(hub_root)
    workspaces = registry.get("workspaces", [])
    return "\n".join([
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Research Hub</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:24px;line-height:1.45;max-width:1180px}",
        "table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0 22px}",
        "td,th{border:1px solid #ddd;padding:6px;vertical-align:top}",
        "form{border:1px solid #ddd;padding:12px;margin:12px 0;max-width:760px}",
        "input,select{margin:3px 6px 8px 0;padding:5px}",
        "button{padding:5px 10px}",
        "code{background:#f4f4f4;padding:1px 4px}",
        ".msg{background:#eef8ee;border:1px solid #9bc59b;padding:8px;margin:10px 0}",
        "</style></head><body>",
        "<h1>Research Hub</h1>",
        "<p>Lazy workspace control plane. Original workspace files remain authoritative.</p>",
        f"<p class='msg'>{html.escape(message)}</p>" if message else "",
        render_registry(workspaces),
        render_registry_form(),
        render_intake(intake_items),
        render_intake_form(),
        render_proposals(proposals, workspaces),
        "</body></html>",
    ])


def render_registry(workspaces: list[dict[str, Any]]) -> str:
    rows = [
        "<h2>Workspaces</h2>",
        "<table><tr><th>ID</th><th>Machine</th><th>Storage</th><th>Inbox</th><th>Capabilities</th></tr>",
    ]
    for item in workspaces:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('workspace_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('machine_role', '')))}</td>"
            f"<td>{html.escape(str(item.get('storage_role', '')))}</td>"
            f"<td><code>{html.escape(str(item.get('transport', 'local_path')))}:"
            f"{html.escape(str(item.get('inbox_path', '')))}</code></td>"
            f"<td>{html.escape(', '.join(item.get('capabilities', [])))}</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def render_registry_form() -> str:
    return """
<form method="post" action="/registry-add">
  <h3>Add Workspace</h3>
  <input name="workspace_id" placeholder="A" required>
  <input name="machine_role" placeholder="3090 / 4080" required>
  <select name="storage_role">
    <option value="research_ssd">research_ssd</option>
    <option value="archive_hdd">archive_hdd</option>
    <option value="scratch">scratch</option>
  </select>
  <input name="root_hint" placeholder="root hint">
  <input name="tailnet_hint" placeholder="tailnet host">
  <input name="inbox_path" placeholder="inbox path" required>
  <select name="transport">
    <option value="local_path">local_path</option>
    <option value="ssh">ssh</option>
  </select>
  <input name="ssh_host" placeholder="linux-b">
  <input name="ssh_user" placeholder="research">
  <input name="remote_inbox" placeholder="/home/research/.research_hub/inbox">
  <input name="hub_ssh_host" placeholder="linux-a">
  <input name="hub_ssh_user" placeholder="research">
  <input name="hub_ssh_root" placeholder="/data/research_hub">
  <input name="capabilities" placeholder="cuda torch dcase2026">
  <label><input type="checkbox" name="can_store_library_blobs">blob store</label>
  <label><input type="checkbox" name="can_run_training">training</label>
  <button type="submit">Add</button>
</form>
"""


def render_intake(items: list[dict[str, Any]]) -> str:
    rows = [
        "<h2>Intake</h2>",
        "<table><tr><th>Item</th><th>Title</th><th>Kind</th><th>Blob</th><th>Action</th></tr>",
    ]
    for item in items:
        item_id = str(item.get("item_id", ""))
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(item_id)}</code></td>"
            f"<td>{html.escape(str(item.get('title', '')))}</td>"
            f"<td>{html.escape(str(item.get('kind', '')))}</td>"
            f"<td><code>{html.escape(str(item.get('blob_root', '')))}</code></td>"
            "<td>"
            f"<form method='post' action='/dispatch-propose'><input type='hidden' name='item_id' value='{html.escape(item_id)}'><button type='submit'>Propose</button></form>"
            "</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def render_intake_form() -> str:
    return """
<form method="post" action="/intake-add">
  <h3>Add Intake From Hub-Visible Path</h3>
  <input name="source_path" placeholder="C:\\research_materials\\bundle.zip" size="60" required>
  <input name="title" placeholder="Title" required>
  <select name="kind">
    <option value="user_upload">user_upload</option>
    <option value="zip_bundle">zip_bundle</option>
    <option value="folder_bundle">folder_bundle</option>
    <option value="related_work_note">related_work_note</option>
  </select>
  <button type="submit">Add Intake</button>
</form>
"""


def render_proposals(
    proposals: list[dict[str, Any]],
    workspaces: list[dict[str, Any]],
) -> str:
    workspace_ids = [str(item.get("workspace_id", "")) for item in workspaces]
    parts = ["<h2>Dispatch Proposals</h2>"]
    for proposal in proposals:
        proposal_id = str(proposal.get("proposal_id", ""))
        parts.append(f"<h3><code>{html.escape(proposal_id)}</code></h3><ul>")
        for target in proposal.get("recommended_targets", []):
            parts.append(
                "<li>"
                f"<strong>{html.escape(str(target.get('workspace_id', '')))}</strong> "
                f"{html.escape(str(target.get('confidence', '')))} - "
                f"{html.escape(str(target.get('reason', '')))}"
                "</li>"
            )
        parts.append("</ul>")
        parts.append("<form method='post' action='/dispatch-approve'>")
        parts.append(f"<input type='hidden' name='proposal_id' value='{html.escape(proposal_id)}'>")
        parts.append("<select name='workspace_id'>")
        for workspace_id in workspace_ids:
            parts.append(
                f"<option value='{html.escape(workspace_id)}'>{html.escape(workspace_id)}</option>"
            )
        parts.append("</select><button type='submit'>Approve</button></form>")
    return "\n".join(parts)
