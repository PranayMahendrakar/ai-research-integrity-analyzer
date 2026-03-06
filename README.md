# 🔬 AI Research Integrity Analyzer

> Automated detection of statistical anomalies, experimental design problems, and reproducibility concerns in scientific research papers.

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen)](https://pranaymahendrakar.github.io/ai-research-integrity-analyzer/)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What It Does

The AI Research Integrity Analyzer is a Python-based system that automatically scrutinizes scientific research papers for:

1. **Statistical Anomalies** — p-hacking, impossible values, underpowered studies
2. **Experimental Design Flaws** — missing controls, no blinding, inadequate sample size justification
3. **Reproducibility Gaps** — absent data/code sharing, no pre-registration, no ethics approval
4. **Reporting Inconsistencies** — missing effect sizes, inverted CIs, publication bias indicators

Each paper receives a **Credibility Score (0–100)** plus dimension scores for statistical quality, design, reproducibility, and transparency.

---

## 🏗️ Architecture

```
research_paper.txt / .json
         │
         ▼
┌─────────────────────┐
│    paper_parser     │  ← Extracts sections, stats, citations
└─────────┬───────────┘
          │ ParsedPaper
          ▼
┌─────────────────────┐
│ statistical_checker │  ← P-curve, power, impossible values
└─────────┬───────────┘
          │ StatisticalReport
          ▼
┌─────────────────────┐
│experiment_validator │  ← Methods, reproducibility, ethics
└─────────┬───────────┘
          │ ValidationReport
          ▼
┌─────────────────────┐
│  report_generator   │  ← HTML + JSON + Markdown outputs
└─────────┬───────────┘
          │
          ▼
   docs/report.html     ← GitHub Pages
   docs/report.json     ← API/downstream use
   docs/index.html      ← Aggregate dashboard
```

---

## 📦 Modules

### 1. `paper_parser.py` — Paper Parser

Parses raw paper text or JSON into structured `ParsedPaper` objects.

**Key Classes:**
- `PaperParser` — Main parser class
- `ParsedPaper` — Dataclass with all extracted content
- `PaperSection` — Represents one paper section
- `StatisticalClaim` — Single statistical value with context

**Analysis Techniques:**
| Technique | Description |
|-----------|-------------|
| Section Detection | Regex patterns identify Abstract, Methods, Results, Discussion, etc. |
| Statistical Pattern Matching | Extracts p-values, effect sizes, CIs, F/t/chi-square statistics |
| Figure/Table Extraction | Maps figure/table references to their captions |
| Citation Parsing | Splits reference list into individual citations |
| Metadata Extraction | Extracts DOI, year, journal from text context |

---

### 2. `statistical_checker.py` — Statistical Checker

Validates all statistical claims for plausibility and internal consistency.

**Key Classes:**
- `StatisticalChecker` — Main checker
- `StatisticalIssue` — Detected issue with severity and suggestion
- `StatisticalReport` — Complete analysis with score

**Analysis Techniques:**

#### P-Curve Analysis
Detects p-value clustering just below α=0.05 (range: 0.040–0.050). A ratio > 50% of significant p-values in this window is a strong indicator of p-hacking (selective reporting of marginally significant results).

#### Statistical Power Analysis
Estimates post-hoc power using the approximation:
```
n_required = (z_α/2 + z_β)² × 2 / d²   [for α=0.05, power=0.80]
power ≈ Φ(|d|×√(n/2) − 1.96)
```
Studies with estimated power < 80% are flagged as underpowered.

#### Impossible Value Detection
- P-values outside [0, 1]
- Correlations outside [−1, 1]
- Effect sizes d > 5 (implausibly large)
- Exact p = 0 (report as p < 0.001)
- Inverted confidence intervals (lower ≥ upper)

#### Confidence Interval Validation
Checks that CIs use standard confidence levels (90%, 95%, 99%) and that bounds are logically ordered.

---

### 3. `experiment_validator.py` — Experiment Validator

Checks for completeness of experimental design and reproducibility indicators.

**Key Classes:**
- `ExperimentValidator` — Main validator
- `ValidationIssue` — Categorized issue with suggestion
- `ValidationReport` — Scores for design, reproducibility, transparency

**Checklist Items:**

| Category | Criteria Checked |
|----------|-----------------|
| **Methods** | Sample size justification, randomization, blinding, control groups, inclusion/exclusion criteria, outcome pre-specification, analysis plan, effect size reporting |
| **Reproducibility** | Data availability, code availability, pre-registration (OSF/ClinicalTrials), materials availability, replication |
| **Ethics** | IRB/ethics approval, informed consent, conflict of interest, funding disclosure |
| **Results** | Confidence intervals reported, effect sizes present, figures included |

**Standards Referenced:**
- [TOP Guidelines](https://www.cos.io/initiatives/top-guidelines) (Transparency & Openness Promotion)
- [CONSORT](https://www.consort-statement.org/) (Consolidated Standards of Reporting Trials)
- [PRISMA](https://prisma-statement.org/) (Systematic Reviews/Meta-Analyses)

---

### 4. `report_generator.py` — Report Generator

Generates HTML, JSON, and Markdown outputs for GitHub Pages and downstream use.

**Output Types:**

| Output | Description |
|--------|-------------|
| `{id}.html` | Full interactive HTML report with color-coded scores and issue cards |
| `{id}.json` | Machine-readable JSON for API/automation |
| Markdown | GitHub Issues/PR-compatible summary |
| `docs/index.html` | Aggregate dashboard of all analyzed papers |

**Credibility Score Formula:**
```
Overall = Statistical × 0.35 + Design × 0.30 + Reproducibility × 0.20 + Transparency × 0.15
```

**Score Thresholds:**
| Score | Rating |
|-------|--------|
| 90–100 | 🟢 Excellent |
| 75–89 | 🟡 Good |
| 60–74 | 🟠 Fair |
| 40–59 | 🔴 Poor |
| 0–39 | 🔴 Critical |

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/PranayMahendrakar/ai-research-integrity-analyzer.git
cd ai-research-integrity-analyzer
# No external dependencies required — uses Python standard library only
```

### Usage

```bash
# Run the built-in demo analysis
python analyzer.py --demo

# Analyze a text file
python analyzer.py --text my_paper.txt --output docs/

# Analyze a JSON-structured paper
python analyzer.py --json paper_data.json --output docs/

# Batch analyze multiple papers
python analyzer.py --batch paper1.txt paper2.txt paper3.json

# Custom paper ID
python analyzer.py --text paper.txt --paper-id my-paper-2024
```

### Python API

```python
from analyzer import ResearchIntegrityAnalyzer

analyzer = ResearchIntegrityAnalyzer(output_dir="docs/")

with open("my_paper.txt") as f:
    text = f.read()

report = analyzer.analyze_text(text, title="My Research Paper")

print(f"Credibility Score: {report['credibility_score']}/100")
print(f"Red Flags: {len(report['red_flags'])}")

analyzer.print_summary(report)
```

---

## 📊 Example Output

```
============================================================
  RESEARCH INTEGRITY ANALYSIS REPORT
============================================================
  Paper: CBT Meta-Analysis Demo
  Date:  2026-03-06
------------------------------------------------------------
  Overall Credibility:  [████████████████░░░░] 82/100
  Statistical:          [████████████████████] 95/100
  Experimental Design:  [██████████████░░░░░░] 73/100
  Reproducibility:      [████████████░░░░░░░░] 60/100
  Transparency:         [████████████████████] 100/100
------------------------------------------------------------

  🚩 RED FLAGS (1):
    [HIGH] No a priori power analysis found. Estimated power 56%.

  💡 REPRODUCIBILITY SUGGESTIONS:
    • Add data availability statement with repository link (OSF/Zenodo)
    • Share analysis code via GitHub or supplementary materials
============================================================
  HTML report: docs/cbt-meta-demo.html
  JSON report: docs/cbt-meta-demo.json
============================================================
```

---

## 🌐 GitHub Pages

Reports are published automatically to GitHub Pages when you run the analyzer and push the `docs/` folder.

**Enable GitHub Pages:**
1. Go to **Settings → Pages**
2. Source: **Deploy from branch**
3. Branch: **main**, Folder: **/docs**
4. Your reports will be live at: `https://PranayMahendrakar.github.io/ai-research-integrity-analyzer/`

---

## 📁 Repository Structure

```
ai-research-integrity-analyzer/
├── analyzer.py              # Main entry point & orchestrator
├── paper_parser.py          # Module 1: Paper parsing
├── statistical_checker.py   # Module 2: Statistical analysis
├── experiment_validator.py  # Module 3: Experimental validation
├── report_generator.py      # Module 4: Report generation
├── docs/
│   ├── index.html           # GitHub Pages dashboard
│   ├── {paper-id}.html      # Individual HTML reports
│   └── {paper-id}.json      # Individual JSON reports
└── README.md
```

---

## 🔍 Detected Issue Types

| Issue Type | Severity | Description |
|------------|----------|-------------|
| `impossible_p_value` | Critical | P-value > 1 or < 0 |
| `impossible_correlation` | Critical | |r| > 1 |
| `inverted_confidence_interval` | Critical | Lower bound ≥ upper bound |
| `p_hacking_suspected` | High | >50% p-values cluster near 0.05 |
| `underpowered_study` | High/Medium | Estimated power < 80% |
| `implausible_effect_size` | High | Cohen's d > 5 |
| `all_results_significant` | Medium | Every reported result is p < 0.05 |
| `missing_ethics_approval` | High | No IRB/ethics statement |
| `missing_data_availability` | High | No data sharing statement |
| `missing_power_analysis` | High | No sample size justification |
| `missing_control_group` | Medium | No control/comparison condition |
| `missing_pre_registration` | Medium | No pre-registration found |
| `missing_code_availability` | Medium | No analysis code shared |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for scientific rigor and research transparency.*
