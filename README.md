# ValdoZ Protocol v3.0

ValdoZ turns Google Antigravity into a disciplined, autonomous delivery partner.

## Installation

Using `uv`:
```bash
uv tool install valdoz-protocol@3.0.0
# Or for local development:
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Quick Start

```bash
# Initialize a new project
valdoz project init

# Start an agent session
valdoz session start --role builder

# Check current phase status
valdoz phase status

# Gate check
valdoz gate check

# Interactive human approval
valdoz phase approve
```
