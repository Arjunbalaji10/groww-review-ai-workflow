# Groww Review Intelligence Workflow

## Overview

An AI workflow that analyzes Groww app reviews, identifies recurring product issues and potential fee confusion, and generates a weekly product pulse and a reusable customer-facing fee clarification.

## Features

- Validate and analyze review data.
- Discover and classify product feedback themes.
- Identify fee-related reviews and categorize candidate issues.
- Generate a weekly product pulse and customer email draft.
- Provide approval-gated MCP tools for supported local-file operations.
- Save reports and draft outputs locally.

## Project Structure

- `data/` — raw review dataset and analysis files.
- `outputs/` — product pulse, analysis summary, and draft outputs.
- `src/mcp_server.py` — MCP server and its supported tools.
- `source_urls.md` — source references.
- `Evidensces/` — screenshots of workflow and MCP tests.

## Setup

Use a Python version supported by the project's installed dependencies.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a local `.env` file with your own `GROQ_API_KEY` and, if needed, `GROQ_MODEL`. Never commit API keys or `.env` to GitHub.

## Run the Dashboard

```bash
python -m streamlit run app.py
```

## Run the MCP Server

```bash
python src/mcp_server.py
```

To test with MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector python src/mcp_server.py
```

## Approval and Outputs

The workflow includes approval checks for supported MCP operations. The current dashboard supports local report and draft outputs. It does **not** publish to a live Google Doc or create an email draft in Gmail; Google Docs and Gmail integrations are not configured. Do not describe a local export as a completed external action.

## Research Limitations

The raw dataset contains 12,835 reviews. The classified dataset currently contains 865 reviews, or approximately **6.74%** of the raw dataset. Findings are preliminary and may not represent the full review population.

The fee candidate dataset contains 339 reviews across five candidate categories. These categories indicate possible themes for further review; they do not verify incorrect charges or establish a billing error.

Use the official Groww references in `source_urls.md` when preparing customer-facing fee explanations. Review the generated content before using or sending it.