# Evaluation & Results: Compliance Check and Corrections

## Compliance Summary (Based on Repo Artifacts)

- The reported quantitative results (e.g., 20 queries, 93% correctness, 18.4 triples/query, 2.3 hops, 85–100% robustness) are **not backed by stored pipeline outputs** in the repository.
- The repo contains **example GraphRAG evidence outputs** for specific single queries, but no dataset of 20 queries or aggregated metrics.
- Therefore, the provided Evaluation & Results section **does not comply with actual logged results** currently present in the codebase.

## What Is Supported by Current Artifacts

### 1) IFC Test Model
- The repository includes the reduced IFC file used for RDF ingestion:
  - `data/processed/rdf/20210125Prova_reduced.ifc`

### 2) GraphRAG Evidence Outputs (Single-Query Examples)
- There are **two evidence JSON files**, each representing a single query execution:
  - `data/processed/evidence.json`
  - `data/processed/rag/evidence.json`
- These include:
  - A single natural-language question
  - Seed entities
  - Nodes and edges in the evidence neighborhood

### 3) Mock Telemetry Pipeline
- TimescaleDB mock telemetry is seeded via:
  - `api/telemetry.py` (endpoint `/telemetry/seed/{point_id}`)
- Schema creation for `telemetry_sample` is defined in:
  - `scripts/init_timescaledb.py`

## What Is NOT Supported by Current Artifacts

- No recorded dataset of **20 evaluation queries** grouped into 4 classes.
- No stored results table for **query correctness**, **coverage**, **interpretability**, **interoperability**, or **robustness**.
- No logs or JSON exports indicating **accuracy rates** or **robustness rates**.
- No recorded counts for **average triples returned per query** or **average hops**.

## Suggested Corrections (LaTeX-Ready Replacement Text)

### Replace Quantitative Claims With Artifact-Backed Statements

```latex
\subsection{Evaluation Setup}
We evaluate \emph{RiG-X} using a reproducible pipeline built on a publicly available IFC residential model and simulated telemetry streams. The IFC-SPF model is converted to RDF and loaded into GraphDB, with semantic overlays from Brick and ASHRAE 223P. Telemetry is represented as mock time-series data in TimescaleDB. 

For this paper we report qualitative evidence from executed GraphRAG queries and pipeline artifacts; large-scale quantitative benchmarking is left for future work.
```

```latex
\subsection{Results}
We report representative GraphRAG evidence outputs from the pipeline. Two example queries were executed and saved as evidence graphs, showing the seed entities, neighborhood nodes, and explanatory triples returned by the SPARQL-based GraphRAG module.

Example artifacts:
\begin{itemize}
  \item \texttt{data/processed/evidence.json} — query: ``Which storey is TERMINALE AERAULICO 2677 on?''
  \item \texttt{data/processed/rag/evidence.json} — query: ``Which terminals are downstream of Apparecchiatura 2881?''
\end{itemize}

These artifacts confirm the pipeline’s ability to retrieve spatial and system-level context from IFC-derived RDF graphs and expose it as interpretable neighborhoods. Formal accuracy, robustness, and coverage benchmarks will be reported in future work after systematic query evaluation.
```

### Optional Minimal Table (Qualitative Only)

```latex
\begin{table}[H]
  \caption{Qualitative evaluation evidence (artifact-backed)}
  \label{tab:qual_eval}
  \centering
  \begin{tabular}{@{}p{0.25\columnwidth}p{0.65\columnwidth}@{}}
    \toprule
    Evidence Type & Source Artifact \\
    \midrule
    GraphRAG evidence (spatial/system-level) & \texttt{data/processed/evidence.json} \\
    GraphRAG evidence (system connectivity) & \texttt{data/processed/rag/evidence.json} \\
    Telemetry mock storage schema & \texttt{scripts/init_timescaledb.py} \\
    \bottomrule
  \end{tabular}
\end{table}
```

## If You Want Quantitative Metrics

To produce the previously claimed metrics, you would need to:
- Define a fixed query set (e.g., 20 queries across 4 classes).
- Log per-query correctness labels.
- Count evidence triples and graph hops per query.
- Aggregate accuracy/coverage/robustness into reproducible tables.

I can help implement this evaluation pipeline and generate those tables if you want, but the current repository does not contain the necessary outputs.
