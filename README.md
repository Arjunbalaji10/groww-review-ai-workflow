\# Groww Review Analysis AI Workflow



\## Overview

An AI workflow that analyzes Groww app reviews, identifies recurring product issues and potential fee confusion, and generates a weekly product pulse and customer-facing fee clarification.



\## Features

\- Validate and analyze review data.

\- Discover and classify review themes.

\- Identify reviews mentioning fees and charges.

\- Generate a weekly product pulse and fee explanation.

\- Use MCP tools with approval checks before writing updates or creating an email draft.

\- Save approved updates and email drafts locally.



\## Project Structure

\- `data/` — raw review dataset and analysis files.

\- `outputs/` — product pulse, analysis summary, and draft outputs.

\- `src/mcp\_server.py` — MCP server and approval-gated tools.

\- `source\_urls.md` — source references.

\- `Evidensces/` — screenshots of MCP tests.



\## Setup

Use Python 3.10 or newer if supported by the installed dependencies.



```bash

python -m pip install -r requirements.txt

```



Create a local `.env` file containing your own `GROQ\_API\_KEY` and, if required, `GROQ\_MODEL`. Never commit `.env` or API keys.



\## Run the MCP Server

```bash

python src/mcp\_server.py

```



To test with MCP Inspector:

```bash

npx -y @modelcontextprotocol/inspector python src/mcp\_server.py

```



\## Approval and Outputs

The MCP tools require approval parameters before writing updates or creating a draft. Outputs are saved locally under `outputs/`. The email tool creates a draft file only; it does not send email.



\*\*Limitation:\*\* Google Docs and Gmail OAuth integrations are not configured. This version uses local files rather than writing to a live Google Doc or creating a draft in Gmail.



\## Research Limitations

The review classification is preliminary and may cover only a subset of the available reviews. Fee-related review text indicates reported user confusion; it does not establish that a fee was incorrectly charged. Refer to official Groww pages in `source\_urls.md` for fee information.



