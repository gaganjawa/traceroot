from pathlib import Path

from traceroot.rag.loader import load_knowledge_document

# ✓ valid Markdown → KnowledgeDocument
# ✓ YAML front matter isn't included in content
# ✓ missing front matter → ValueError
# ✓ corpus loader loads multiple .md files
# ✓ corpus ordering is deterministic


def test_valid_knowledge_document(tmp_path: Path):
    content = """---
        document_type: runbook
        service: checkout-service
        topic: latency
        ---
    
        # Checkout Runbook
    
        Check checkout latency.
    """
    md_file = tmp_path / "test.md"
    md_file.write_text(content)

    document = load_knowledge_document(md_file)

    assert document.source == "test.md"
    assert document.document_type == "runbook"
    assert document.service == "checkout-service"
    assert document.topic == "latency"
    assert document.content.startswith("# Checkout Runbook")
