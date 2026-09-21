"""Validate Markdown sources and stage supported, traceable text uploads."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
import yaml

ROOT = Path(__file__).resolve().parents[1]
KB_NAMES = ("account_billing_kb", "product_policy_kb")


def load_knowledge(directory: Path = ROOT / "knowledge") -> list[dict]:
    documents = []
    for name in KB_NAMES:
        path = directory / f"{name}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("name") != name or data.get("spec_version") != "v1":
            raise ValueError(f"{path.name}: expected a v1 knowledge base named {name}.")
        kb = KnowledgeBase.model_validate(data, extra="forbid")
        kb.validate_documents_or_index_exists()
        paths = data.get("documents", [])
        if not isinstance(paths, list) or not 1 <= len(paths) <= 100 or any(not isinstance(p, str) for p in paths):
            raise ValueError(f"{name}: documents must list 1-100 Markdown paths.")
        domain = name.removesuffix("_kb")
        domain_dir = (directory / "docs" / domain).resolve()
        resolved = []
        for entry in paths:
            source = (directory / entry).resolve()
            if source.parent != domain_dir or source.suffix != ".md":
                raise ValueError(f"{name}: source must be a Markdown file in docs/{domain}/.")
            content = source.read_bytes()
            if not content or len(content) > 5_000_000:
                raise ValueError(f"{source.name}: empty or exceeds the 5 MB text upload limit.")
            text = content.decode("utf-8")
            if not text.startswith("# ") or "Document ID:" not in text:
                raise ValueError(f"{source.name}: add a title and stable Document ID.")
            resolved.append(source)
        if len(set(resolved)) != len(resolved):
            raise ValueError(f"{name}: duplicate source document.")
        if set(resolved) != set(domain_dir.glob("*.md")):
            raise ValueError(f"{name}: every Markdown file in the domain must be listed exactly once.")
        documents.append(data)
    return documents


def build_knowledge(
    directory: Path = ROOT / "knowledge", output: Path = ROOT / ".build" / "knowledge",
) -> list[Path]:
    sources = load_knowledge(directory)  # Validate everything before writing.
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"format_version": 1, "knowledge_bases": {}}
    files = []
    for source_spec in sources:
        data = deepcopy(source_spec)
        entries = []
        uploads = []
        for relative in data["documents"]:
            source = directory / relative
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            # A content change gets a different upload name. Readiness checks can
            # then distinguish old ingested documents from the new local sources.
            upload_relative = Path("documents") / data["name"] / f"{source.stem}_{digest[:12]}.txt"
            upload = output / upload_relative
            upload.parent.mkdir(parents=True, exist_ok=True)
            upload.write_bytes(content)  # Markdown is UTF-8 text; no facts are transformed.
            uploads.append(upload_relative.as_posix())
            entries.append({"source": relative, "upload": upload_relative.as_posix(), "sha256": digest})
        data["documents"] = uploads
        path = output / f"{data['name']}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        KnowledgeBase.from_spec(str(path)).validate_documents_or_index_exists()
        manifest["knowledge_bases"][data["name"]] = entries
        files.append(path)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Staged {sum(len(d['documents']) for d in sources)} Markdown sources for {len(files)} knowledge bases in {output}.")
    return files


def assert_knowledge_ready(client, files: list[Path]) -> None:
    """Require ready indexes containing exactly the expected uploaded documents."""
    for path in files:
        spec = KnowledgeBase.from_spec(str(path))
        matches = client.get_by_names([spec.name])
        if len(matches) != 1 or not matches[0].get("id"):
            raise RuntimeError(f"{spec.name}: expected exactly one imported knowledge base in the active workspace.")
        status = client.status(matches[0]["id"])
        state = str(status.get("built_in_index_status", "unknown")).lower()
        if state != "ready" or status.get("ready") is False:
            raise RuntimeError(f"{spec.name}: ingestion state is {state}; inspect `orchestrate knowledge-bases status --name {spec.name} --verbose` before retrying.")
        expected = {Path(p).name for p in spec.documents}
        actual = [d.get("metadata", {}).get("original_file_name") for d in status.get("documents", [])]
        if set(actual) != expected or len(actual) != len(expected):
            raise RuntimeError(f"{spec.name}: ingested document names do not match the current source manifest; stopping before agent import.")
        print(f"{spec.name}: ready with all {len(expected)} expected documents.")
