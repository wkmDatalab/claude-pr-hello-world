# Agentic Mapping: Claude Agent SDK to Future Cortex Code SDK

This repo is the non-Snowflake version of the pattern you will later reuse with Cortex Code.

## Same idea

```text
prompt -> model decides -> tool call -> SDK executes -> tool result -> model continues -> final/report
```

## Current Claude version

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

options = ClaudeAgentOptions(
    cwd=ROOT,
    allowed_tools=["Read", "Glob", "Grep", "Bash", "Write"],
    max_turns=8,
)
```

## Future Cortex version

```python
from cortex_code_agent_sdk import CortexCodeAgentOptions, CortexCodeSDKClient

options = CortexCodeAgentOptions(
    cwd=ROOT,
    connection="my-snowflake-connection",
    allowed_tools=["Read", "Glob", "Grep", "Bash", "Write"],
    max_turns=8,
)
```

## Important concept mapping

| Concept | This repo | Later Cortex version |
|---|---|---|
| Agent run | `ClaudeSDKClient.query(...)` | `CortexCodeSDKClient.query(...)` |
| Working directory | `cwd=ROOT` | `cwd=ROOT` |
| Safe command execution | `Bash` tool with hooks | `Bash` tool with hooks |
| Report output | `reports/*.md` | same, or Snowflake table |
| Traceability | `traceability/events.jsonl` | same, plus Snowflake audit table |
| Data validation | `pytest` | `pytest`, SQL checks, Snowflake queries |
| GitHub hosted PR | not included | optional via GitHub CLI/API/MCP |

## Why this is useful

Once you understand the loop here, Snowflake becomes a target system, not a new mental model.

The SDK orchestration pattern remains:

```text
configure environment
configure tools
configure safety rules
send prompt
stream messages
capture artifacts
log traceability
let human approve
```
