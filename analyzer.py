"""
analyzer.py - Main entry point for the AI Research Integrity Analyzer.

Usage:
    python analyzer.py --text "path/to/paper.txt" --output docs/
    python analyzer.py --json "path/to/paper.json" --output docs/
    python analyzer.py --demo  (runs on built-in demo paper)

This orchestrates all four modules:
    paper_parser -> statistical_checker -> experiment_validator -> report_generator
"""

import argparse
import json
import os
import sys
from typing import Optional

from paper_parser import PaperParser
from statistical_checker import StatisticalChecker
from experiment_validator import ExperimentValidator
from report_generator import ReportGenerator


class ResearchIntegrityAnalyzer:
    """
    Orchestrates the full research integrity analysis pipeline.

    Pipeline:
    1. PaperParser    - Extracts structured content from raw paper text
    2. StatisticalChecker - Validates statistical claims and detects anomalies
    3. ExperimentValidator - Checks experimental design and reproducibility
    4. ReportGenerator - Produces HTML/JSON reports for GitHub Pages
    """

    def __init__(self, output_dir: str = "docs"):
        self.parser = PaperParser()
        self.checker = StatisticalChecker()
        self.validator = ExperimentValidator()
        self.generator = ReportGenerator(output_dir=output_dir)
        self.output_dir = output_dir

    def analyze_text(self, text: str, title: str = "Unknown Paper",
                     paper_id: Optional[str] = None) -> dict:
        """
        Analyze a paper from raw text.

        Args:
            text: Raw text content of the paper
            title: Paper title (optional, extracted from text if not given)
            paper_id: Unique ID for this paper (optional, generated if not given)

        Returns:
            Complete report data dictionary
        """
        print(f"[1/4] Parsing paper: {title[:60]}")
        paper = self.parser.parse_text(text, title)
        print(f"      Found {len(paper.sections)} sections, {len(paper.statistical_claims)} statistical claims")

        print("[2/4] Running statistical analysis...")
        stat_report = self.checker.check(paper)
        print(f"      Statistical score: {stat_report.statistical_score:.0f}/100 | Issues: {len(stat_report.issues)}")

        print("[3/4] Validating experimental design...")
        val_report = self.validator.validate(paper)
        print(f"      Design score: {val_report.design_score:.0f} | Repro: {val_report.reproducibility_score:.0f} | Trans: {val_report.transparency_score:.0f}")

        print("[4/4] Generating report...")
        report_data = self.generator.generate_full_report(paper, stat_report, val_report, paper_id)
        print(f"      Overall credibility score: {report_data['credibility_score']}/100")
        print(f"      Red flags: {len(report_data['red_flags'])}")

        return report_data

    def analyze_json(self, json_data: dict, paper_id: Optional[str] = None) -> dict:
        """Analyze a paper from a JSON structured format."""
        title = json_data.get('title', 'Unknown Paper')
        print(f"[1/4] Parsing JSON paper: {title[:60]}")
        paper = self.parser.parse_json(json_data)
        print(f"      Found {len(paper.sections)} sections, {len(paper.statistical_claims)} statistical claims")

        print("[2/4] Running statistical analysis...")
        stat_report = self.checker.check(paper)

        print("[3/4] Validating experimental design...")
        val_report = self.validator.validate(paper)

        print("[4/4] Generating report...")
        report_data = self.generator.generate_full_report(paper, stat_report, val_report, paper_id)

        return report_data

    def analyze_file(self, file_path: str, paper_id: Optional[str] = None) -> dict:
        """Analyze a paper from a file (text or JSON)."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if file_path.endswith('.json'):
            data = json.loads(content)
            return self.analyze_json(data, paper_id)
        else:
            basename = os.path.basename(file_path).replace('.txt', '').replace('.md', '')
            return self.analyze_text(content, title=basename, paper_id=paper_id)

    def analyze_batch(self, file_paths: list) -> list:
        """Analyze multiple papers and update the index."""
        all_reports = []
        for path in file_paths:
            try:
                report = self.analyze_file(path)
                all_reports.append(report)
                print(f"✅ Completed: {path}")
            except Exception as e:
                print(f"❌ Failed: {path} - {e}")

        # Update the GitHub Pages index
        self.generator.update_index(all_reports)
        print(f"\n📄 Index updated: {self.output_dir}/index.html")
        return all_reports

    def print_summary(self, report_data: dict):
        """Print a formatted summary to the console."""
        scores = report_data['scores']
        red_flags = report_data['red_flags']

        def bar(score, width=20):
            filled = int(score / 100 * width)
            return '[' + '█' * filled + '░' * (width - filled) + f'] {score:.0f}/100'

        print("\n" + "="*60)
        print("  RESEARCH INTEGRITY ANALYSIS REPORT")
        print("="*60)
        print(f"  Paper: {report_data['paper']['title'][:55]}")
        print(f"  Date:  {report_data['timestamp'][:10]}")
        print("-"*60)
        print(f"  Overall Credibility:  {bar(scores['overall'])}")
        print(f"  Statistical:          {bar(scores['statistical'])}")
        print(f"  Experimental Design:  {bar(scores['design'])}")
        print(f"  Reproducibility:      {bar(scores['reproducibility'])}")
        print(f"  Transparency:         {bar(scores['transparency'])}")
        print("-"*60)

        if red_flags:
            print(f"\n  🚩 RED FLAGS ({len(red_flags)}):")
            for flag in red_flags[:5]:
                sev = flag['severity'].upper()
                print(f"    [{sev}] {flag['description'][:70]}")
        else:
            print("\n  ✅ No critical red flags detected.")

        if report_data['reproducibility_suggestions']:
            print(f"\n  💡 REPRODUCIBILITY SUGGESTIONS:")
            for s in report_data['reproducibility_suggestions'][:3]:
                print(f"    • {s[:70]}")

        print("\n" + "="*60)
        print(f"  HTML report: {self.output_dir}/{report_data['paper_id']}.html")
        print(f"  JSON report: {self.output_dir}/{report_data['paper_id']}.json")
        print("="*60 + "\n")


DEMO_PAPER = """
The Effects of Cognitive Behavioral Therapy on Depression: A Meta-Analysis

Authors: Emily Chen, Michael Torres, Sarah Williams

Abstract
This meta-analysis examined the efficacy of cognitive behavioral therapy (CBT)
for depression across 52 randomized controlled trials (N = 4,891). CBT showed
a large, significant effect (Cohen's d = 0.89, p < 0.001, 95% CI [0.76, 1.02]).
Subgroup analyses by format (individual vs. group) and duration were conducted.
Pre-registered at PROSPERO (CRD42024001234). Data available at osf.io/cbt-meta.

Keywords: cognitive behavioral therapy, depression, meta-analysis, effect size

Introduction
Depression affects approximately 280 million people worldwide. CBT is a leading
psychological treatment but effect sizes vary considerably across studies...

Methods
Inclusion criteria: RCTs of CBT for adults with diagnosed depression.
Exclusion criteria: Studies without control groups, non-English publications.
Sample sizes ranged from 18 to 247 participants per study.
Power analysis: 80% power to detect d=0.5 (small-to-medium) required n=128.
Random assignment was verified for all included studies.
Raters were blinded to study outcomes during quality assessment.
Primary outcome: BDI-II or PHQ-9 at post-treatment.
Statistical analysis: Random-effects meta-analysis using R (metafor package).
Ethics: Systematic review exempt from ethics review.

Results
Overall effect: d = 0.89, p < 0.001, 95% CI [0.76, 1.02], k = 52 studies.
Heterogeneity: I2 = 67%, Q(51) = 154.3, p < 0.001.
Individual CBT: d = 0.95, n = 31 studies, p < 0.001.
Group CBT: d = 0.74, n = 21 studies, p = 0.003.
Publication bias: Egger's test p = 0.08. Trim-and-fill: 3 studies imputed.
Funnel plot asymmetry present but non-significant.
Moderator analysis: Session count correlated with effect size, r = 0.31, p = 0.024.

Discussion
CBT demonstrates robust, large effects on depression. Effect sizes are consistent
with prior meta-analyses. Limitations include heterogeneity across studies...

Conflict of Interest: Authors declare no competing interests.
Funding: Supported by NIMH grant R21MH128543.
Data Availability: All data and analysis code available at https://osf.io/cbt-meta
Analysis code: https://github.com/example/cbt-meta-analysis
"""


def main():
    parser = argparse.ArgumentParser(
        description='AI Research Integrity Analyzer - Detect problems in scientific papers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyzer.py --demo
  python analyzer.py --text paper.txt --output docs/
  python analyzer.py --json paper.json --title "My Paper"
  python analyzer.py --batch paper1.txt paper2.txt paper3.json
        """
    )
    parser.add_argument('--text', help='Path to a text file of the paper')
    parser.add_argument('--json', help='Path to a JSON file of the paper')
    parser.add_argument('--title', default='', help='Paper title override')
    parser.add_argument('--output', default='docs', help='Output directory (default: docs)')
    parser.add_argument('--batch', nargs='+', help='Analyze multiple files')
    parser.add_argument('--demo', action='store_true', help='Run analysis on built-in demo paper')
    parser.add_argument('--paper-id', default=None, help='Custom paper ID')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')

    args = parser.parse_args()

    analyzer = ResearchIntegrityAnalyzer(output_dir=args.output)

    if args.demo:
        print("Running demo analysis on built-in sample paper...\n")
        report = analyzer.analyze_text(DEMO_PAPER, "CBT Meta-Analysis Demo", paper_id="demo-cbt-meta")
        analyzer.print_summary(report)
        # Also update index
        analyzer.generator.update_index([report])
        print(f"GitHub Pages index updated: {args.output}/index.html")

    elif args.batch:
        print(f"Batch analyzing {len(args.batch)} files...\n")
        reports = analyzer.analyze_batch(args.batch)
        print(f"\nBatch complete: {len(reports)} papers analyzed.")
        for r in reports:
            analyzer.print_summary(r)

    elif args.text:
        report = analyzer.analyze_file(args.text, args.paper_id)
        analyzer.print_summary(report)

    elif args.json:
        with open(args.json) as f:
            data = json.load(f)
        if args.title:
            data['title'] = args.title
        report = analyzer.analyze_json(data, args.paper_id)
        analyzer.print_summary(report)

    else:
        print("No input specified. Use --demo to run a demonstration.")
        print("Run 'python analyzer.py --help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
