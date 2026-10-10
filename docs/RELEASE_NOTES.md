# Draft release notes

## Proposed v1.2.0 — Remote MCP Transport & Production Hardening

**Unreleased draft.** Latest local release tag: `v1.1.0`; `v1.0-capstone` remains
the historical research milestone. A backward-compatible feature warrants a MINOR
release. No tag or release has been created by this cleanup.

### New features

- Optional Streamable HTTP MCP transport using the installed MCP 2.2.0 SDK, with
  validated URL/timeout configuration and one session per synchronous tool call.
- Preserved default in-process MCP execution and stdio server launch. HTTP exposes
  the same four tools at `/mcp`, with unchanged inputs, evidence models, and Agent
  and EvidenceBackend contracts.
- Best-effort failed investigation persistence retains partial state and failure
  metadata while preserving the original error.

### Reliability/hardening

- Shared bounded evidence context limits prompt-facing observations while retaining
  stored investigation evidence.
- Telemetry validation and provenance from v1.1.0 remain preserved: malformed
  Loki/Prometheus responses fail explicitly; complete labels and distinct Loki
  stream identities survive evidence serialization. This is retained functionality,
  not a newly introduced full provenance framework.
- GitHub release pagination has finite bounds and non-progress detection.
- Comparison runs use isolated output directories; frozen results remain untouched.
- Embeddings initialize lazily when needed.
- Remote tool responses validate structured result lists and evidence entries;
  connection/protocol errors propagate and session resources close on exit.

### Evaluation improvements

- Stop-reason evaluation aligns with runtime reasons while preserving the historical
  `two_empty_results` alias.
- Affected Service Accuracy and Explanation Faithfulness broaden RCA evaluation.
- Current validation baseline: **1,205 passed**; Ruff format and lint checks pass.
- These post-capstone improvements do not change historical experiment conclusions.
  No evaluation/comparison artifacts were regenerated for this release draft.

### Known limitations

- A separate MCP server owns its backend/runtime state and defaults to fixtures.
  Client/UI live registries and configuration are not transferred; remote live
  evidence requires explicit backend/runtime setup inside the server process.
- MCP environment settings apply to the optional adapter; existing CLI/UI executors
  are not automatically switched to MCP.
- No authentication, TLS management, retries/backoff, service discovery, persistent
  sessions, or Kubernetes/deployment orchestration is added.
- The adapter remains synchronous with `asyncio.run()` and cannot be invoked directly
  inside an already-running event loop. Per-call sessions incur connection overhead.
- Failure persistence is best-effort, not durable checkpointing. Fuller query/source
  provenance and production readiness remain follow-up work.

### Release preparation note

No existing changelog/release-notes file or release automation was found locally.
Package metadata is now aligned to `1.2.0`, with `pyproject.toml` as the version
source and `uv.lock` recording the generated project version. At tag `v1.1.0`,
package metadata historically reported `0.1.0`. This remains an unreleased draft;
remote release state was not queried.
