# Project Plan: `finago-ai-copilot`

**Subtitle:** *Production Reference Architecture for B2B Financial & Payroll GenAI (Finago Ask, Automate, Build)*

---

## 1. Objective & Finago Alignment

This project demonstrates end-to-end production AI Engineering tailored to Finago's core AI pillars:

1. **Finago Ask** ([Procountor Ask Help Docs](https://help.procountor.fi/en/articles/531497-finago-procountor-mobile-ask-ai-assistant)):
   - Conversational analytics over sales/purchase invoices and income statements.
   - Domain defaults: excludes VAT (`ex_vat=True`) by default, filters by `invoice_date` (or `posting_date` on request), and attaches an `interpretation_note` explaining how the query was interpreted.
   - **Collective Agreement Assistant**: Hybrid RAG over the official Finnish Collective Agreement with mandatory `§` section citations, strictly gated by user payroll permissions (`has_payroll_rights=True`).
   - Natural-language/voice draft invoice creation (`can_create_invoices=True`).

2. **Finago Automate** ([Finago AI Overview](https://finago.com/ai/) & [Sept 24, 2026 Press Release](https://finago.com/news/finago-launches-new-ai-capabilities-and-opens-its-platform-for-customers-to-build-their-own-ai-agents/)):
   - **Two-Tier Document Understanding (OCR + Vision Fallback)**:
     - **Tier 1**: Fast, zero-cost local `RapidOCR` text extraction + `Pydantic AI` structured output.
     - **Accounting Checksum Gate**: Deterministic Pydantic validation checking `Net + VAT == Gross` and OCR confidence threshold.
     - **Tier 2**: Automatic escalation to Multimodal Vision LLM (`BinaryContent`) only when Tier 1 fails the accounting checksum or confidence gate—keeping latency and token cost under control.
   - **Auto-Posting & Anomaly Detection**: Predicts General Ledger (GL) account codes, flags duplicate invoices or amounts exceeding `2x` historical vendor averages, and saves entries as `DRAFT_PENDING_APPROVAL` for human accountability.

3. **Finago Build** ([Finago AI Overview](https://finago.com/ai/) & [Sept 24, 2026 Press Release](https://finago.com/news/finago-launches-new-ai-capabilities-and-opens-its-platform-for-customers-to-build-their-own-ai-agents/)):
   - **Model Context Protocol (MCP) Server** (`FastMCP`) + **FastAPI** service.
   - Exposes `mcp_accountant_morning_triage` so accounting offices can run a morning agent across multiple SME client ledgers to surface overdue invoices, missing receipts, and flagged anomalies within user approval limits.

---

## 2. Data Sources (Real Public Data)

1. **Real B2B Invoices (`katanaml-org/invoices-donut-data-v1` on Hugging Face)**:
   - Contains 500 real scanned B2B invoices with ground-truth JSON annotations (`invoice_no`, `seller`, `client`, `invoice_date`, `items[]`, `total_net_worth`, `total_vat`, `total_gross_worth`).
   - All 500 structured invoice records populate the SQLite ledger (`data/procountor_ledger.db`) for SQL reporting and anomaly baselines.
   - Scanned invoice images are saved locally (`data/invoices/`) to benchmark the Two-Tier OCR pipeline against ground-truth totals.

2. **Real Payroll Policy ([Collective Agreement of the IT Service Sector in Finland 2025–2027](https://tietoala.fi/wp-content/uploads/2026/09/TES_englanti_2025_korj_2_9_2026.pdf))**:
   - Official English text published by Technology Industry Employers of Finland, YTN, and Tietoala (`data/finnish_it_tes_2025_2027.md`).
   - Covers `§ 12 Additional work, overtime and Sunday work`, `§ 14–19 Sick & family leave`, `§ 20 Annual holiday`, `§ 21 Holiday bonus (lomaraha)`, `§ 23 Travel expenses`, and termination notice periods.

---

## 3. Database & Reproducibility Design

- **Database Engine**: Python standard-library `sqlite3` (`data/procountor_ledger.db`, configurable via `DB_PATH`).
- **Why `.gitignore` `*.db`**: Binary SQLite files cause noisy diffs when mutated during local testing. Instead, `src/db/db.py` deterministically initializes and populates `procountor_ledger.db` from the downloaded dataset in `<0.5s`.
- **Reproducibility (Docker + Offline Fallback)**:
  - Multi-stage `Dockerfile` and `docker-compose.yml` pin all dependencies and pre-bake the SQLite ledger and OCR runtime weights during build.
  - Supports **Live LLM Mode** (when `OPENAI_API_KEY` is set) and **Deterministic Test/Offline Mode** (using `Pydantic AI`'s `FunctionModel` / `TestModel`), guaranteeing `pytest` and `docker compose up` work out-of-the-box for any reviewer.

---

## 4. Incremental PR Roadmap

We deliver the project in **9 small, single-responsibility Pull Requests**:

| PR # | Branch Name | Scope & Deliverable | Verification / Test |
| :--- | :--- | :--- | :--- |
| **PR #1** | `chore/repo-scaffold` | Repo skeleton, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.gitignore`, `.github/workflows/ci.yml`, and `PLAN.md`. | CI workflow syntax & container config check |
| **PR #2** | `feat/dataset-downloader` | Script to fetch B2B invoices from `katanaml-org/invoices-donut-data-v1` and extract the official Finnish IT Collective Agreement (`TES 2025–2027`). | `tests/test_dataset.py` |
| **PR #3** | `feat/sqlite-ledger-db` | SQLite schema (Tenants, Users/RBAC, GL Accounts, Invoices, Line Items) and loader populating all 500 real B2B invoice records. | `tests/test_db.py` |
| **PR #4** | `feat/ocr-tier1-and-validator` | **Finago Automate (Part 1):** Local `RapidOCR` text extraction + Pydantic `Net + VAT == Gross` accounting checksum validator. | `tests/test_ocr_validator.py` |
| **PR #5** | `feat/ocr-vision-fallback-and-anomalies` | **Finago Automate (Part 2):** Tier-2 Vision LLM fallback when Tier-1 fails the checksum + duplicate/amount anomaly detection + `DRAFT_PENDING_APPROVAL` workflow. | `tests/test_ocr_fallback.py` |
| **PR #6** | `feat/ask-sql-reporting-tool` | **Finago Ask (Part 1):** `Pydantic AI` SQL reporting tool enforcing Procountor defaults (`ex-VAT`, `invoice_date`) and returning `interpretation_note`. | `tests/test_ask_sql.py` |
| **PR #7** | `feat/ask-payroll-rag-and-rbac` | **Finago Ask (Part 2):** Hybrid Search (BM25 + vector) over Finnish TES (`§` citations) + hard RBAC guard (`has_payroll_rights`) + draft invoice creation tool. | `tests/test_ask_rbac.py` |
| **PR #8** | `feat/build-fastapi-and-mcp` | **Finago Build:** FastAPI REST endpoints (`/ask`, `/automate/ocr`) + MCP server (`mcp_accountant_morning_triage`) + latency/cost telemetry. | `tests/test_server.py` |
| **PR #9** | `docs/eval-gate-and-adr` | End-to-end Evaluation Benchmark suite, `docs/ADR-001-pydantic-ai-vs-langchain.md` (focusing on LangChain over-abstraction vs thin primitives), and final `README.md`. | `tests/test_eval_suite.py` |
