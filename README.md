<div align="center">

<img src="assets/hero.svg" alt="Cloud Analyst: Make your data make sense. An AI data analyst assistant" width="100%">

<br>

<img src="https://img.shields.io/badge/Python-3.10%2B-7658e8?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
<img src="https://img.shields.io/badge/Flask-API-7658e8?style=flat-square&logo=flask&logoColor=white" alt="Flask">
<img src="https://img.shields.io/badge/React-19-7658e8?style=flat-square&logo=react&logoColor=white" alt="React 19">
<img src="https://img.shields.io/badge/Vite-frontend-7658e8?style=flat-square&logo=vite&logoColor=white" alt="Vite">
<img src="https://img.shields.io/badge/pandas-analysis-7658e8?style=flat-square&logo=pandas&logoColor=white" alt="pandas">
<img src="https://img.shields.io/badge/LangChain-agent-7658e8?style=flat-square" alt="LangChain">
<img src="https://img.shields.io/badge/Groq-LLM-7658e8?style=flat-square" alt="Groq">

<br><br>

**[Overview](#overview)** &nbsp;·&nbsp;
**[Features](#features)** &nbsp;·&nbsp;
**[How it works](#how-it-works)** &nbsp;·&nbsp;
**[Quick start](#quick-start)** &nbsp;·&nbsp;
**[API reference](#api-reference)** &nbsp;·&nbsp;
**[Complete report](#complete-report)** &nbsp;·&nbsp;
**[Security](#security-and-limitations)**

</div>

<img src="assets/divider.svg" alt="" width="100%">

## Overview

**Cloud Analyst** is a chat-based data analyst. Upload a CSV or Excel file, ask a question in plain language, and get an answer calculated from your actual rows. A tool-calling **pandas agent** (LangChain + Groq) runs the calculations, so results come from your data instead of the model's memory.

Prefer a full picture over a single answer? One click produces a **complete analysis report** covering data quality, numeric summaries, outliers, correlations and recommended next steps. The report is computed with pandas alone, with no LLM call.

<div align="center">
<img src="assets/chat-demo.svg" alt="Animated demo: a question is typed, the assistant analyzes the data, then replies with a table" width="100%">
<br>
<sub>Mock-up of the real interface. Figures come from the bundled sample dataset (<code>backend/uploads/report.csv</code>).</sub>
</div>

<br>

## Features

<img src="assets/features.svg" alt="Six features: plain-language questions, CSV and Excel upload, one-click report, readable answers, automatic column typing, self-hosted workspace" width="100%">

<br>

### What you can ask

The repository ships with a sample file, `report.csv`: loan-pool performance for 15 quarterly vintages (2021-Q1 to 2024-Q3), 375 rows by 16 columns. Try prompts like these once it is uploaded:

| Prompt | What the agent does |
|---|---|
| *Which vintage has the highest cumulative net loss rate?* | Groups by `VintageID` and compares peak `CumulativeNetLossRate` |
| *Compare net loss rate across vintages at 12 months on book.* | Filters `MonthsOnBook == 12` and ranks vintages |
| *How does 30+ day delinquency change with months on book?* | Aggregates `CurrentDelinq30Plus` by `MonthsOnBook` |
| *Which numeric columns are most correlated with PoolFactor?* | Computes Pearson correlations |
| *Summarize this dataset and highlight the key takeaways.* | Built-in suggestion card in the UI |

<img src="assets/divider.svg" alt="" width="100%">

## How it works

<img src="assets/architecture.svg" alt="Animated architecture diagram: React UI, Flask API, report engine, pandas DataFrame, LangChain agent and Groq LLM" width="100%">

<br>

Three request routes share one in-memory DataFrame:

| Route | Path through the system | Uses an LLM? |
|---|---|:---:|
| **Upload** | UI → Flask parses the file with pandas → stored as `current_df` → 5-row preview returned | No |
| **Analyze** | UI → Flask → `build_analysis_report()` → Markdown report rendered in chat | No |
| **Query** | UI → Flask → LangChain pandas agent → Groq model plans and runs pandas code → Markdown answer | Yes |

### Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, Vite, `react-markdown`, `remark-gfm`, oxlint |
| Backend | Flask, Flask-CORS, python-dotenv |
| Data | pandas, openpyxl / xlrd for Excel files |
| AI | LangChain (`langchain-groq`, `langchain-experimental`), Groq-hosted model |

<img src="assets/divider.svg" alt="" width="100%">

## Quick start

**Prerequisites:** Python 3.10+ (developed on 3.13), Node.js 20.19+ or 22.12+, and a free [Groq API key](https://console.groq.com/keys).

### 1. Clone

```bash
git clone <your-repo-url>
cd ai-data-analyst-assistant
```

### 2. Start the backend

```bash
cd backend/uploads

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt

cp .env.example .env               # then edit .env and add your key
python app.py
```

The API now listens on **http://localhost:5000**. Open that address and you should see `{"status": "ok", "message": "Backend is running"}`.

### 3. Start the frontend

In a second terminal:

```bash
cd frontend/my-react-app
npm install
npm run dev
```

Open the URL Vite prints (usually **http://localhost:5173**), upload `backend/uploads/report.csv`, and ask your first question.

> [!NOTE]
> The frontend calls the backend at `http://localhost:5000`, which is set directly in `src/App.jsx`. Change it there if you run the API on another host or port.

### Configuration

| Setting | Where | Default |
|---|---|---|
| `GROQ_API_KEY` | `backend/uploads/.env` | none (required for questions; uploads and reports work without it) |
| Model name, temperature, `max_tokens` | `get_llm()` in `app.py` | temperature `0.1`, `max_tokens` `512` |
| Backend port | last line of `app.py` | `5000` |
| Accepted file types | `upload_file()` in `app.py` | `.csv`, `.xlsx`, `.xls` |

<img src="assets/divider.svg" alt="" width="100%">

## API reference

Base URL: `http://localhost:5000`

| Method | Endpoint | Body | Success response |
|---|---|---|---|
| `GET` | `/` | none | `{ "status": "ok", "message": "Backend is running" }` |
| `POST` | `/api/upload` | `multipart/form-data`, field `file` (`.csv`, `.xlsx`, `.xls`) | `{ "message", "summary": { filename, rows, columns, columns_names, preview } }` |
| `DELETE` | `/api/upload` | none | `{ "message": "Uploaded dataset deleted" }` |
| `POST` | `/api/analyze` | none | `{ "report": "<Markdown>" }` |
| `POST` | `/api/query` | JSON `{ "query": "..." }` | `{ "query": "...", "result": "<Markdown>" }` |

Errors return `{ "error": "..." }` with status `400` (no file, unsupported format, empty query, no dataset uploaded) or `500` (parse, analysis or model failure).

<details>
<summary><b>Example: call the API with curl</b></summary>

```bash
# 1. Upload the sample dataset
curl -F "file=@backend/uploads/report.csv" http://localhost:5000/api/upload

# 2. Ask a question
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Which vintage has the highest cumulative net loss rate?"}'

# 3. Generate the complete report
curl -X POST http://localhost:5000/api/analyze

# 4. Remove the dataset from memory
curl -X DELETE http://localhost:5000/api/upload
```

</details>

<img src="assets/divider.svg" alt="" width="100%">

## Complete report

The **Generate complete report** button calls `/api/analyze` and renders a Markdown report in the chat. It never guesses: every figure is computed from the uploaded DataFrame.

| Section | What it contains |
|---|---|
| Executive summary | Row and column counts, column-type mix, missing cells, duplicate rows |
| Data quality | Per-column type, missing count and percentage, distinct values |
| Numeric column summaries | Mean, median, standard deviation, min, quartiles, max, IQR outlier count |
| Numeric distributions | Text histograms for up to six numeric columns |
| Categorical column summaries | Top five values per column with counts and shares |
| Date/time coverage | Parseable value counts and date range per date column |
| Relationships | Top ten Pearson correlation pairs |
| Recommended next steps | Follow-ups based on missing data, duplicates and outliers |

Outlier flags are screening signals, not proof of errors, and correlation does not imply causation. The report says so itself.

## Project structure

```text
ai-data-analyst-assistant/
├── assets/                     README graphics (animated SVG)
├── backend/
│   ├── requirements.txt
│   └── uploads/
│       ├── app.py              Flask API, report builder, LangChain agent
│       ├── report.csv          Sample dataset (loan-pool vintages)
│       └── .env.example        Copy to .env and add GROQ_API_KEY
├── frontend/
│   └── my-react-app/
│       ├── src/
│       │   ├── App.jsx         Chat UI, upload flow, report button
│       │   ├── App.css         Styles
│       │   └── main.jsx        Entry point
│       ├── index.html
│       ├── package.json
│       └── vite.config.js
├── .gitignore
└── README.md
```

<img src="assets/divider.svg" alt="" width="100%">

## Security and limitations

> [!WARNING]
> **Run this locally or in a sandbox. Do not expose it to the internet as-is.**
> The query agent is created with `allow_dangerous_code=True`, which lets the model-written Python execute on the machine running the backend. That is what makes real calculations possible, and it is also why the server must not be reachable by untrusted users.

| Area | Current behavior | Suggested hardening |
|---|---|---|
| Code execution | LLM-generated pandas code runs in the Flask process | Run in a container or sandbox with no secrets and limited filesystem access |
| Data sharing | `/api/query` sends your question and a data preview to the Groq API | Review Groq's data policy before using sensitive data; use `/api/analyze` for fully local analysis |
| Sessions | One dataset is stored in a global variable, shared by every client | Key the dataset by session or user ID |
| Server mode | `debug=True` and CORS open to all origins | Disable debug and restrict origins outside development |
| Answer length | `max_tokens=512` can truncate long answers | Raise it in `get_llm()` |
| Reliability | Model answers can be wrong | Verify important results, as the UI reminds you |

## Roadmap ideas

- [ ] Per-session datasets so several people can use one server
- [ ] Charts rendered in chat (line, bar, scatter) from query results
- [ ] Streaming answers for faster perceived response
- [ ] Downloadable report as PDF or Markdown
- [ ] Docker Compose setup for one-command start
- [ ] Automated tests for `build_analysis_report()` and the API routes

## Contributing

Issues and pull requests are welcome. For larger changes, open an issue first to discuss the approach. Run `npm run lint` in `frontend/my-react-app` before submitting frontend changes.

## License

No license file is included yet. Add one (for example MIT) before sharing the project publicly.

<br>

<div align="center">
<img src="assets/logo.svg" alt="Cloud Analyst logo" width="48">
<br>
<sub>Built with Flask, React, pandas, LangChain and Groq.</sub>
</div>
