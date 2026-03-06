"""
report_generator.py - Generates HTML and JSON integrity reports for GitHub Pages.

Outputs:
- HTML report with credibility score, red flags, reproducibility suggestions
- JSON data for API consumption
- Markdown summary for GitHub issues
- GitHub Pages index.html
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from paper_parser import ParsedPaper
from statistical_checker import StatisticalReport, StatisticalIssue
from experiment_validator import ValidationReport, ValidationIssue


class ReportGenerator:
    """
    Generates comprehensive integrity reports for research papers.

    Output Types:
    1. HTML Report: Full interactive report for GitHub Pages with color-coded
       scores, issue cards, and reproducibility checklists.
    2. JSON Report: Machine-readable data for downstream processing.
    3. Markdown Summary: Concise summary for GitHub Issues or PR comments.
    4. GitHub Pages Index: Aggregate index of all analyzed papers.
    """

    SEVERITY_COLORS = {
        'critical': '#dc3545',
        'high': '#fd7e14',
        'medium': '#ffc107',
        'low': '#0dcaf0'
    }

    SCORE_COLORS = {
        'excellent': '#28a745',   # 90-100
        'good': '#6fbf73',        # 75-89
        'fair': '#ffc107',        # 60-74
        'poor': '#fd7e14',        # 40-59
        'critical': '#dc3545'     # 0-39
    }

    def __init__(self, output_dir: str = "docs"):
        """
        Args:
            output_dir: Directory for GitHub Pages output (default: 'docs')
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_full_report(
        self,
        paper: ParsedPaper,
        stat_report: StatisticalReport,
        val_report: ValidationReport,
        paper_id: Optional[str] = None
    ) -> Dict:
        """
        Generate a complete integrity report combining all analysis results.
        Returns the report data dict and creates output files.
        """
        paper_id = paper_id or self._generate_id(paper.title)
        timestamp = datetime.now().isoformat()

        # Calculate overall credibility score
        credibility_score = self._calculate_credibility_score(stat_report, val_report)
        red_flags = self._collect_red_flags(stat_report, val_report)
        reproducibility_suggestions = self._collect_reproducibility_suggestions(val_report)

        report_data = {
            'paper_id': paper_id,
            'timestamp': timestamp,
            'paper': {
                'title': paper.title,
                'authors': paper.authors,
                'abstract': paper.abstract[:500] if paper.abstract else '',
                'sections_count': len(paper.sections),
                'statistical_claims_count': len(paper.statistical_claims),
                'figures_count': len(paper.figures),
                'tables_count': len(paper.tables),
                'references_count': len(paper.references),
                'metadata': paper.metadata
            },
            'credibility_score': credibility_score,
            'scores': {
                'statistical': stat_report.statistical_score,
                'design': val_report.design_score,
                'reproducibility': val_report.reproducibility_score,
                'transparency': val_report.transparency_score,
                'overall': credibility_score
            },
            'red_flags': red_flags,
            'reproducibility_suggestions': reproducibility_suggestions,
            'statistical_analysis': {
                'p_values': stat_report.p_values,
                'effect_sizes': stat_report.effect_sizes,
                'sample_sizes': stat_report.sample_sizes,
                'p_curve_suspicious': stat_report.p_curve_suspicious,
                'underpowered': stat_report.underpowered,
                'issues': [
                    {'type': i.issue_type, 'severity': i.severity,
                     'description': i.description, 'suggestion': i.suggestion}
                    for i in stat_report.issues
                ]
            },
            'validation_analysis': {
                'checklist': val_report.checklist,
                'issues': [
                    {'category': i.category, 'severity': i.severity,
                     'description': i.description, 'suggestion': i.suggestion}
                    for i in val_report.issues
                ]
            }
        }

        # Generate output files
        html_path = os.path.join(self.output_dir, f"{paper_id}.html")
        json_path = os.path.join(self.output_dir, f"{paper_id}.json")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_html_report(report_data))

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return report_data

    def _calculate_credibility_score(self, stat_report: StatisticalReport,
                                      val_report: ValidationReport) -> float:
        """
        Calculate overall credibility score as weighted average:
        - Statistical score: 35%
        - Design score: 30%
        - Reproducibility score: 20%
        - Transparency score: 15%
        """
        score = (
            stat_report.statistical_score * 0.35 +
            val_report.design_score * 0.30 +
            val_report.reproducibility_score * 0.20 +
            val_report.transparency_score * 0.15
        )
        return round(score, 1)

    def _collect_red_flags(self, stat_report: StatisticalReport,
                            val_report: ValidationReport) -> List[Dict]:
        """Collect all high/critical severity issues as red flags."""
        red_flags = []

        for issue in stat_report.issues:
            if issue.severity in ('critical', 'high'):
                red_flags.append({
                    'source': 'statistical',
                    'type': issue.issue_type,
                    'severity': issue.severity,
                    'description': issue.description,
                    'suggestion': issue.suggestion
                })

        for issue in val_report.issues:
            if issue.severity in ('critical', 'high'):
                red_flags.append({
                    'source': 'validation',
                    'type': issue.category,
                    'severity': issue.severity,
                    'description': issue.description,
                    'suggestion': issue.suggestion
                })

        # Sort by severity: critical first
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        red_flags.sort(key=lambda x: severity_order.get(x['severity'], 4))
        return red_flags

    def _collect_reproducibility_suggestions(self, val_report: ValidationReport) -> List[str]:
        """Extract reproducibility-specific suggestions."""
        suggestions = []
        for issue in val_report.issues:
            if issue.category == 'reproducibility' and issue.suggestion:
                suggestions.append(issue.suggestion)
        return suggestions

    def _get_score_color(self, score: float) -> str:
        """Return color code for a score."""
        if score >= 90:
            return self.SCORE_COLORS['excellent']
        elif score >= 75:
            return self.SCORE_COLORS['good']
        elif score >= 60:
            return self.SCORE_COLORS['fair']
        elif score >= 40:
            return self.SCORE_COLORS['poor']
        else:
            return self.SCORE_COLORS['critical']

    def _get_score_label(self, score: float) -> str:
        """Return text label for a score."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"

    def _generate_id(self, title: str) -> str:
        """Generate a URL-safe ID from paper title."""
        import re
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
        words = clean.split()[:5]
        slug = '-'.join(words)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M')
        return f"{slug}-{timestamp}"

    def generate_html_report(self, report_data: Dict) -> str:
        """Generate a full HTML report for GitHub Pages."""
        paper = report_data['paper']
        scores = report_data['scores']
        red_flags = report_data['red_flags']
        suggestions = report_data['reproducibility_suggestions']
        stat = report_data['statistical_analysis']
        val = report_data['validation_analysis']

        overall_color = self._get_score_color(scores['overall'])
        overall_label = self._get_score_label(scores['overall'])

        # Build issue cards HTML
        def issue_card(issue, source=''):
            color = self.SEVERITY_COLORS.get(issue.get('severity', 'low'), '#6c757d')
            return f"""
            <div class="issue-card" style="border-left: 4px solid {color}; padding: 12px; margin: 8px 0; background: #f8f9fa; border-radius: 4px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong>{issue.get('type', issue.get('category', 'Issue')).replace('_', ' ').title()}</strong>
                    <span class="badge" style="background:{color}; color:white; padding:2px 8px; border-radius:12px; font-size:0.8em;">
                        {issue.get('severity', '').upper()}
                    </span>
                </div>
                <p style="margin: 8px 0 4px;">{issue.get('description', '')}</p>
                {f'<p style="color:#6c757d; font-size:0.9em; margin:0;"><em>Suggestion: {issue.get("suggestion", "")}</em></p>' if issue.get('suggestion') else ''}
            </div>"""

        red_flag_cards = '\n'.join([issue_card(f) for f in red_flags]) if red_flags else '<p style="color:green;">No critical red flags detected.</p>'

        stat_issue_cards = '\n'.join([issue_card(i, 'stat') for i in stat['issues']]) if stat['issues'] else '<p style="color:green;">No statistical issues detected.</p>'
        val_issue_cards = '\n'.join([issue_card(i, 'val') for i in val['issues']]) if val['issues'] else '<p style="color:green;">No validation issues detected.</p>'

        # Checklist HTML
        checklist_html = '<table style="width:100%; border-collapse:collapse;">'
        checklist_html += '<tr><th style="text-align:left;padding:6px;border-bottom:2px solid #dee2e6;">Criterion</th><th style="padding:6px;border-bottom:2px solid #dee2e6;">Status</th></tr>'
        for key, passed in val['checklist'].items():
            status_icon = '✅' if passed == 'PASS' or passed is True else '❌'
            label = key.replace('_', ' ').title()
            checklist_html += f'<tr><td style="padding:6px;border-bottom:1px solid #dee2e6;">{label}</td><td style="text-align:center;padding:6px;border-bottom:1px solid #dee2e6;">{status_icon}</td></tr>'
        checklist_html += '</table>'

        suggestions_html = '<ul>' + '\n'.join([f'<li>{s}</li>' for s in suggestions]) + '</ul>' if suggestions else '<p>No additional reproducibility suggestions.</p>'

        score_circle = lambda score, label: f"""
        <div style="text-align:center; margin:10px;">
            <div style="width:80px;height:80px;border-radius:50%;background:{self._get_score_color(score)};
                        display:flex;align-items:center;justify-content:center;margin:0 auto;color:white;font-size:1.3em;font-weight:bold;">
                {score:.0f}
            </div>
            <div style="margin-top:6px;font-size:0.9em;color:#6c757d;">{label}</div>
        </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Integrity Report - {paper['title'][:60]}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #212529; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
        .score-hero {{ display: flex; align-items: center; gap: 20px; }}
        .score-circle {{ width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2em; font-weight: bold; color: white; }}
        .card {{ background: white; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .scores-grid {{ display: flex; justify-content: space-around; flex-wrap: wrap; }}
        .section-title {{ font-size: 1.3em; font-weight: 600; color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 8px; margin-bottom: 16px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; color: white; }}
        footer {{ text-align: center; color: #6c757d; font-size: 0.85em; margin-top: 40px; }}
    </style>
</head>
<body>

<div class="header">
    <div class="score-hero">
        <div class="score-circle" style="background:{overall_color};">{scores['overall']:.0f}</div>
        <div>
            <h1 style="margin:0 0 6px;">{paper['title'][:80]}</h1>
            <p style="margin:0; opacity:0.9;">Overall Credibility: <strong>{overall_label}</strong></p>
            <p style="margin:4px 0 0; font-size:0.85em; opacity:0.75;">Analyzed: {report_data['timestamp'][:19].replace('T', ' ')}</p>
        </div>
    </div>
</div>

<div class="card">
    <div class="section-title">Score Breakdown</div>
    <div class="scores-grid">
        {score_circle(scores['statistical'], 'Statistical')}
        {score_circle(scores['design'], 'Design')}
        {score_circle(scores['reproducibility'], 'Reproducibility')}
        {score_circle(scores['transparency'], 'Transparency')}
    </div>
</div>

<div class="card">
    <div class="section-title">Paper Summary</div>
    <table style="width:100%; border-collapse:collapse;">
        <tr><td style="padding:4px;color:#6c757d;">Authors</td><td style="padding:4px;">{', '.join(paper['authors']) if paper['authors'] else 'Not extracted'}</td></tr>
        <tr><td style="padding:4px;color:#6c757d;">Sections</td><td style="padding:4px;">{paper['sections_count']}</td></tr>
        <tr><td style="padding:4px;color:#6c757d;">Statistical Claims</td><td style="padding:4px;">{paper['statistical_claims_count']}</td></tr>
        <tr><td style="padding:4px;color:#6c757d;">P-values Found</td><td style="padding:4px;">{len(stat['p_values'])}</td></tr>
        <tr><td style="padding:4px;color:#6c757d;">P-curve Suspicious</td><td style="padding:4px;">{'⚠️ Yes' if stat['p_curve_suspicious'] else '✅ No'}</td></tr>
        <tr><td style="padding:4px;color:#6c757d;">Underpowered</td><td style="padding:4px;">{'⚠️ Yes' if stat['underpowered'] else '✅ No'}</td></tr>
    </table>
</div>

<div class="card">
    <div class="section-title">🚩 Red Flags ({len(red_flags)})</div>
    {red_flag_cards}
</div>

<div class="card">
    <div class="section-title">📊 Statistical Analysis Issues</div>
    {stat_issue_cards}
</div>

<div class="card">
    <div class="section-title">🔬 Experimental Validation Issues</div>
    {val_issue_cards}
</div>

<div class="card">
    <div class="section-title">✅ Reproducibility Checklist</div>
    {checklist_html}
</div>

<div class="card">
    <div class="section-title">💡 Reproducibility Suggestions</div>
    {suggestions_html}
</div>

<footer>
    <p>Generated by AI Research Integrity Analyzer | Report ID: {report_data['paper_id']}</p>
    <p><a href="index.html">← Back to All Reports</a></p>
</footer>
</body>
</html>"""

        return html

    def generate_markdown_summary(self, report_data: Dict) -> str:
        """Generate a Markdown summary for GitHub Issues/PRs."""
        paper = report_data['paper']
        scores = report_data['scores']
        red_flags = report_data['red_flags']

        def score_emoji(s):
            if s >= 90: return "🟢"
            elif s >= 75: return "🟡"
            elif s >= 60: return "🟠"
            else: return "🔴"

        md = f"""## Research Integrity Analysis Report

**Paper:** {paper['title']}
**Overall Credibility Score:** {score_emoji(scores['overall'])} **{scores['overall']}/100**

### Score Breakdown
| Dimension | Score | Rating |
|-----------|-------|--------|
| Statistical | {scores['statistical']:.0f}/100 | {score_emoji(scores['statistical'])} {self._get_score_label(scores['statistical'])} |
| Design | {scores['design']:.0f}/100 | {score_emoji(scores['design'])} {self._get_score_label(scores['design'])} |
| Reproducibility | {scores['reproducibility']:.0f}/100 | {score_emoji(scores['reproducibility'])} {self._get_score_label(scores['reproducibility'])} |
| Transparency | {scores['transparency']:.0f}/100 | {score_emoji(scores['transparency'])} {self._get_score_label(scores['transparency'])} |

### 🚩 Red Flags ({len(red_flags)})
"""
        if red_flags:
            for flag in red_flags[:5]:
                md += f"- **[{flag['severity'].upper()}]** {flag['description']}\n"
        else:
            md += "No critical red flags detected.\n"

        md += f"""
### Reproducibility Status
- P-curve Suspicious: {'⚠️ Yes' if report_data['statistical_analysis']['p_curve_suspicious'] else '✅ No'}
- Underpowered: {'⚠️ Yes' if report_data['statistical_analysis']['underpowered'] else '✅ No'}

*Generated by AI Research Integrity Analyzer on {report_data['timestamp'][:10]}*
"""
        return md

    def update_index(self, reports: List[Dict]):
        """Update the GitHub Pages index.html with all analyzed papers."""
        rows = ""
        for r in sorted(reports, key=lambda x: x.get('credibility_score', 0)):
            score = r.get('credibility_score', 0)
            color = self._get_score_color(score)
            title = r.get('paper', {}).get('title', 'Unknown')[:60]
            paper_id = r.get('paper_id', '')
            flags = len(r.get('red_flags', []))
            date = r.get('timestamp', '')[:10]

            rows += f"""<tr>
                <td><a href="{paper_id}.html">{title}</a></td>
                <td style="text-align:center;"><span style="background:{color};color:white;padding:2px 8px;border-radius:12px;">{score}</span></td>
                <td style="text-align:center;">{'🚩 ' + str(flags) if flags else '✅ 0'}</td>
                <td style="text-align:center;color:#6c757d;">{date}</td>
            </tr>\n"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Research Integrity Analyzer - Reports</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; }}
        h1 {{ background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        table {{ width:100%; border-collapse:collapse; }}
        th {{ background:#f8f9fa; padding:10px; text-align:left; border-bottom:2px solid #dee2e6; }}
        td {{ padding:10px; border-bottom:1px solid #dee2e6; }}
        tr:hover {{ background:#f8f9fa; }}
        a {{ color:#667eea; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
        .hero {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; padding:40px; border-radius:12px; margin-bottom:30px; }}
    </style>
</head>
<body>
<div class="hero">
    <h1 style="-webkit-text-fill-color:white; background:none;">🔬 AI Research Integrity Analyzer</h1>
    <p>Automated detection of statistical issues, experimental design problems, and reproducibility concerns in scientific papers.</p>
    <p><strong>{len(reports)}</strong> papers analyzed</p>
</div>

<h2>Analyzed Papers</h2>
<table>
    <thead>
        <tr>
            <th>Paper Title</th>
            <th style="text-align:center;">Credibility Score</th>
            <th style="text-align:center;">Red Flags</th>
            <th style="text-align:center;">Date</th>
        </tr>
    </thead>
    <tbody>
        {rows if rows else '<tr><td colspan="4" style="text-align:center;color:#6c757d;">No papers analyzed yet. Run the analyzer to generate reports.</td></tr>'}
    </tbody>
</table>

<hr style="margin:40px 0; border:none; border-top:1px solid #dee2e6;">
<h2>How It Works</h2>
<p>The AI Research Integrity Analyzer uses four specialized modules:</p>
<ol>
    <li><strong>paper_parser</strong> – Extracts structured content: sections, statistical claims, figures, citations.</li>
    <li><strong>statistical_checker</strong> – Detects p-hacking, underpowered studies, impossible values, and CI errors.</li>
    <li><strong>experiment_validator</strong> – Checks for missing methodological details, ethics reporting, and reproducibility.</li>
    <li><strong>report_generator</strong> – Produces HTML/JSON reports with credibility scores and actionable suggestions.</li>
</ol>
<p style="color:#6c757d; font-size:0.9em;">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | <a href="https://github.com/PranayMahendrakar/ai-research-integrity-analyzer">View on GitHub</a></p>
</body>
</html>"""

        index_path = os.path.join(self.output_dir, "index.html")
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return index_path


if __name__ == "__main__":
    from paper_parser import PaperParser
    from statistical_checker import StatisticalChecker
    from experiment_validator import ExperimentValidator

    sample_text = """
    A Randomized Controlled Trial of Mindfulness-Based Stress Reduction
    Smith J, Doe A, Johnson R

    Abstract
    We conducted a double-blind RCT (n = 120) to evaluate mindfulness training.
    Primary outcome: anxiety scores. Results significant: p = 0.031, Cohen's d = 0.52,
    95% CI [0.18, 0.86]. IRB approved. Data available at osf.io/example.

    Keywords: mindfulness, anxiety, RCT, stress reduction

    Methods
    Participants randomly assigned to mindfulness (n=60) or waitlist control (n=60).
    Power analysis: 80% power to detect d=0.5 required n=128.
    Ethics: Approved by University IRB (Protocol 2024-001).
    Informed consent obtained from all participants.
    Pre-registered at ClinicalTrials.gov: NCT12345.

    Results
    Mindfulness group showed significant reduction: t(118) = 2.45, p = 0.016.
    Cohen's d = 0.52. 95% CI [0.18, 0.86]. r = 0.29.

    Conflict of interest: No conflicts declared.
    Funded by: NIH Grant R01MH123456.
    Data available at: https://osf.io/example
    """

    parser = PaperParser()
    paper = parser.parse_text(sample_text, "Mindfulness RCT")

    checker = StatisticalChecker()
    stat_report = checker.check(paper)

    validator = ExperimentValidator()
    val_report = validator.validate(paper)

    generator = ReportGenerator(output_dir="docs")
    report_data = generator.generate_full_report(paper, stat_report, val_report)

    print(f"Credibility Score: {report_data['credibility_score']}/100")
    print(f"Red Flags: {len(report_data['red_flags'])}")
    print(f"Suggestions: {len(report_data['reproducibility_suggestions'])}")
    print("\nMarkdown Summary:")
    print(generator.generate_markdown_summary(report_data))
