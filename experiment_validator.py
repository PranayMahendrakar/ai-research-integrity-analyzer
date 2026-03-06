"""
experiment_validator.py - Validates experimental design and identifies missing details.

Checks:
- Presence of key experimental details (controls, blinding, randomization)
- Reproducibility indicators (data availability, code sharing, protocol registration)
- Ethics and consent reporting
- Sample size justification
- Conflict of interest disclosure
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from paper_parser import ParsedPaper


@dataclass
class ValidationIssue:
    """Represents a validation issue found in experimental design."""
    category: str     # design, reproducibility, ethics, reporting, transparency
    severity: str     # low, medium, high, critical
    description: str
    suggestion: str = ""
    section: str = ""


@dataclass
class ValidationReport:
    """Summary of experimental validation results."""
    issues: List[ValidationIssue] = field(default_factory=list)
    checklist: Dict[str, bool] = field(default_factory=dict)
    reproducibility_score: float = 100.0
    design_score: float = 100.0
    transparency_score: float = 100.0


class ExperimentValidator:
    """
    Validates experimental design and reproducibility of research papers.

    Analysis Techniques:
    1. Methods Completeness Scoring: Checks for presence of critical methodological
       details using keyword matching and section analysis.
    2. Reproducibility Checklist: Evaluates against established reproducibility
       standards (e.g., TOP guidelines, CONSORT, PRISMA).
    3. Control Detection: Identifies whether appropriate control conditions are
       described for experimental studies.
    4. Blinding/Randomization Verification: Checks if studies involving human
       subjects report blinding and randomization procedures.
    5. Data/Code Availability: Detects data sharing statements and code repository links.
    6. Pre-registration Detection: Checks for trial/study pre-registration mentions.
    7. Ethics Reporting: Validates presence of IRB/ethics approval statements.
    """

    # Critical experimental detail keywords
    METHODS_CHECKLIST = {
        'sample_size_justification': [
            'power analysis', 'sample size calculation', 'a priori power',
            'required sample size', 'minimum sample size'
        ],
        'randomization': [
            'randomly assigned', 'randomized', 'random allocation',
            'random assignment', 'randomisation', 'block randomization'
        ],
        'blinding': [
            'double-blind', 'single-blind', 'triple-blind', 'masked',
            'blinded', 'assessor blind', 'placebo-controlled'
        ],
        'control_group': [
            'control group', 'control condition', 'control participants',
            'placebo group', 'comparison group', 'waitlist control'
        ],
        'inclusion_exclusion': [
            'inclusion criteria', 'exclusion criteria', 'eligibility criteria',
            'eligible participants', 'recruited participants'
        ],
        'outcome_measures': [
            'primary outcome', 'secondary outcome', 'outcome measure',
            'dependent variable', 'primary endpoint'
        ],
        'statistical_analysis_plan': [
            'statistical analysis', 'analysis plan', 'pre-specified analysis',
            'planned analysis', 'intention-to-treat', 'per-protocol'
        ],
        'effect_size_reporting': [
            "cohen's d", "cohen's f", 'eta squared', 'omega squared',
            'effect size', 'magnitude', 'hedges'
        ],
    }

    # Reproducibility indicators
    REPRODUCIBILITY_CHECKLIST = {
        'data_availability': [
            'data available', 'data are available', 'data accessibility',
            'publicly available', 'open data', 'data repository',
            'supplementary data', 'figshare', 'zenodo', 'osf.io', 'dryad'
        ],
        'code_availability': [
            'code available', 'analysis code', 'source code', 'github',
            'gitlab', 'bitbucket', 'r script', 'python script', 'code repository'
        ],
        'pre_registration': [
            'pre-registered', 'preregistered', 'osf preregistration',
            'aspredicted', 'clinicaltrials.gov', 'trial registration',
            'registered report', 'protocol registration', 'prospero'
        ],
        'materials_availability': [
            'materials available', 'stimuli available', 'instruments available',
            'questionnaire available', 'open materials', 'supplementary materials'
        ],
        'replication': [
            'replication', 'replicated', 'independent replication',
            'conceptual replication', 'direct replication'
        ],
    }

    # Ethics and transparency indicators
    ETHICS_CHECKLIST = {
        'ethics_approval': [
            'irb', 'ethics committee', 'institutional review board',
            'ethics approval', 'approved by', 'ethical approval',
            'research ethics board', 'human subjects committee'
        ],
        'informed_consent': [
            'informed consent', 'written consent', 'verbal consent',
            'participants consented', 'consent obtained', 'assented'
        ],
        'conflict_of_interest': [
            'conflict of interest', 'competing interests', 'no conflict',
            'declare no', 'potential conflict', 'financial disclosure',
            'funding source'
        ],
        'funding_disclosure': [
            'funded by', 'supported by', 'grant from', 'funding source',
            'financial support', 'acknowledged funding', 'no funding'
        ],
    }

    def __init__(self):
        pass

    def validate(self, paper: ParsedPaper) -> ValidationReport:
        """
        Run all validation checks on a parsed paper.
        Returns a ValidationReport with findings and scores.
        """
        report = ValidationReport()
        full_text = paper.raw_text.lower()
        methods_text = ""
        results_text = ""

        # Extract section-specific text
        for section in paper.sections:
            if section.section_type == 'methods':
                methods_text = section.content.lower()
            elif section.section_type == 'results':
                results_text = section.content.lower()

        # Use full text if sections not found
        if not methods_text:
            methods_text = full_text

        # Run checks
        self._check_methods_completeness(paper, full_text, methods_text, report)
        self._check_reproducibility(paper, full_text, report)
        self._check_ethics_transparency(paper, full_text, report)
        self._check_results_completeness(paper, full_text, results_text, report)
        self._check_abstract_consistency(paper, report)

        # Calculate scores
        self._calculate_scores(report)

        return report

    def _check_methods_completeness(self, paper: ParsedPaper, full_text: str,
                                     methods_text: str, report: ValidationReport):
        """Check for presence of critical methodological details."""
        search_text = methods_text if methods_text else full_text

        for criterion, keywords in self.METHODS_CHECKLIST.items():
            found = any(kw in search_text for kw in keywords)
            report.checklist[criterion] = found

            if not found:
                severity, description, suggestion = self._get_methods_issue(criterion)
                report.issues.append(ValidationIssue(
                    category='design',
                    severity=severity,
                    description=description,
                    suggestion=suggestion,
                    section='methods'
                ))

    def _get_methods_issue(self, criterion: str):
        """Get issue details for a missing methods element."""
        issues_map = {
            'sample_size_justification': (
                'high',
                'No a priori power analysis or sample size justification found.',
                'Report power analysis with effect size estimate, alpha level, and target power (≥0.80).'
            ),
            'randomization': (
                'medium',
                'No randomization procedure described (for experimental/RCT studies).',
                'Describe randomization method (e.g., block randomization, stratification) if applicable.'
            ),
            'blinding': (
                'medium',
                'No blinding procedure described for participant/assessor assignments.',
                'Report whether participants, experimenters, and outcome assessors were blinded.'
            ),
            'control_group': (
                'medium',
                'No control group or comparison condition described.',
                'Include an appropriate control/comparison condition to rule out confounds.'
            ),
            'inclusion_exclusion': (
                'high',
                'No inclusion or exclusion criteria reported.',
                'List all inclusion and exclusion criteria to enable sample characterization.'
            ),
            'outcome_measures': (
                'high',
                'Primary and secondary outcome measures not clearly specified.',
                'Pre-specify primary and secondary outcomes with operational definitions.'
            ),
            'statistical_analysis_plan': (
                'medium',
                'Statistical analysis plan not described or pre-specified.',
                'Describe all planned statistical analyses, including corrections for multiple comparisons.'
            ),
            'effect_size_reporting': (
                'medium',
                'Effect size estimates not reported alongside significance tests.',
                'Always report standardized effect sizes (e.g., Cohen\'s d, eta-squared) with confidence intervals.'
            ),
        }
        return issues_map.get(criterion, ('low', f'Missing: {criterion}', ''))

    def _check_reproducibility(self, paper: ParsedPaper, full_text: str, report: ValidationReport):
        """Check for reproducibility indicators."""
        for criterion, keywords in self.REPRODUCIBILITY_CHECKLIST.items():
            found = any(kw in full_text for kw in keywords)
            report.checklist[criterion] = found

            if not found:
                severity, description, suggestion = self._get_reproducibility_issue(criterion)
                report.issues.append(ValidationIssue(
                    category='reproducibility',
                    severity=severity,
                    description=description,
                    suggestion=suggestion
                ))

    def _get_reproducibility_issue(self, criterion: str):
        """Get issue details for a missing reproducibility element."""
        issues_map = {
            'data_availability': (
                'high',
                'No data availability statement found.',
                'Add a data availability statement specifying where data can be accessed (e.g., OSF, Zenodo).'
            ),
            'code_availability': (
                'medium',
                'Analysis code or scripts not made available.',
                'Share analysis code via GitHub, OSF, or supplementary materials for reproducibility.'
            ),
            'pre_registration': (
                'medium',
                'No pre-registration of hypotheses or analysis plan detected.',
                'Pre-register studies at OSF, AsPredicted, or ClinicalTrials.gov before data collection.'
            ),
            'materials_availability': (
                'low',
                'Study materials (stimuli, questionnaires) not explicitly made available.',
                'Share study materials via open repositories or supplementary files.'
            ),
            'replication': (
                'low',
                'No replication attempt or cross-validation reported.',
                'Include a replication study or cross-validation to strengthen findings.'
            ),
        }
        return issues_map.get(criterion, ('low', f'Missing: {criterion}', ''))

    def _check_ethics_transparency(self, paper: ParsedPaper, full_text: str, report: ValidationReport):
        """Check for ethics approvals and transparency disclosures."""
        for criterion, keywords in self.ETHICS_CHECKLIST.items():
            found = any(kw in full_text for kw in keywords)
            report.checklist[criterion] = found

            if not found:
                severity, description, suggestion = self._get_ethics_issue(criterion)
                report.issues.append(ValidationIssue(
                    category='ethics',
                    severity=severity,
                    description=description,
                    suggestion=suggestion
                ))

    def _get_ethics_issue(self, criterion: str):
        """Get issue details for a missing ethics element."""
        issues_map = {
            'ethics_approval': (
                'high',
                'No IRB or ethics committee approval statement found.',
                'Report IRB/ethics approval with protocol number for all human subjects research.'
            ),
            'informed_consent': (
                'high',
                'No informed consent procedure described.',
                'State how informed consent was obtained from all participants.'
            ),
            'conflict_of_interest': (
                'medium',
                'No conflict of interest declaration found.',
                'Include a conflict of interest statement, even if stating no conflicts exist.'
            ),
            'funding_disclosure': (
                'medium',
                'No funding source disclosure found.',
                'Disclose all funding sources and grant numbers.'
            ),
        }
        return issues_map.get(criterion, ('low', f'Missing: {criterion}', ''))

    def _check_results_completeness(self, paper: ParsedPaper, full_text: str,
                                     results_text: str, report: ValidationReport):
        """Check results section completeness."""
        search_text = results_text if results_text else full_text

        # Check for confidence intervals
        if '% ci' not in search_text and 'confidence interval' not in search_text:
            report.issues.append(ValidationIssue(
                category='reporting',
                severity='medium',
                description='Confidence intervals not reported with key results.',
                suggestion='Report 95% CIs alongside point estimates and p-values.',
                section='results'
            ))

        # Check for effect sizes
        effect_keywords = ["cohen's d", 'eta squared', 'omega squared', 'effect size', "hedges' g"]
        if not any(kw in search_text for kw in effect_keywords):
            report.issues.append(ValidationIssue(
                category='reporting',
                severity='medium',
                description='No standardized effect sizes reported in results.',
                suggestion='Add effect size estimates (e.g., d, eta^2) to all key comparisons.',
                section='results'
            ))

        # Check for figure count vs. discussion
        if len(paper.figures) == 0 and len(paper.sections) > 3:
            report.issues.append(ValidationIssue(
                category='reporting',
                severity='low',
                description='No figures detected. Visual data presentation is recommended.',
                suggestion='Include figures showing key data distributions and results.',
                section='results'
            ))

    def _check_abstract_consistency(self, paper: ParsedPaper, report: ValidationReport):
        """Check for consistency between abstract and methods/results."""
        if not paper.abstract:
            report.issues.append(ValidationIssue(
                category='reporting',
                severity='high',
                description='Abstract not found or too short to evaluate.',
                suggestion='Include a structured abstract with background, methods, results, and conclusions.',
            ))
        elif len(paper.abstract) < 100:
            report.issues.append(ValidationIssue(
                category='reporting',
                severity='medium',
                description=f'Abstract is very short ({len(paper.abstract)} chars). May lack key details.',
                suggestion='Expand abstract to include all key methodological and findings details.'
            ))

    def _calculate_scores(self, report: ValidationReport):
        """Calculate dimension scores based on issues found."""
        design_deduct = {'critical': 30, 'high': 15, 'medium': 8, 'low': 3}
        repro_deduct = {'critical': 25, 'high': 20, 'medium': 10, 'low': 5}
        trans_deduct = {'critical': 25, 'high': 15, 'medium': 8, 'low': 3}

        design_score = 100.0
        repro_score = 100.0
        trans_score = 100.0

        for issue in report.issues:
            if issue.category == 'design':
                design_score -= design_deduct.get(issue.severity, 5)
            elif issue.category == 'reproducibility':
                repro_score -= repro_deduct.get(issue.severity, 8)
            elif issue.category in ('ethics', 'transparency'):
                trans_score -= trans_deduct.get(issue.severity, 5)
            elif issue.category == 'reporting':
                design_score -= design_deduct.get(issue.severity, 5) * 0.5

        report.design_score = max(0.0, design_score)
        report.reproducibility_score = max(0.0, repro_score)
        report.transparency_score = max(0.0, trans_score)

    def get_reproducibility_checklist(self, report: ValidationReport) -> Dict[str, str]:
        """Return checklist as pass/fail/missing dict."""
        return {k: ('PASS' if v else 'MISSING') for k, v in report.checklist.items()}

    def get_summary(self, report: ValidationReport) -> Dict:
        """Generate structured summary of validation results."""
        return {
            'design_score': report.design_score,
            'reproducibility_score': report.reproducibility_score,
            'transparency_score': report.transparency_score,
            'overall_score': (report.design_score + report.reproducibility_score + report.transparency_score) / 3,
            'issues_count': len(report.issues),
            'checklist': self.get_reproducibility_checklist(report),
            'issues_by_category': {
                'design': [i for i in report.issues if i.category == 'design'],
                'reproducibility': [i for i in report.issues if i.category == 'reproducibility'],
                'ethics': [i for i in report.issues if i.category == 'ethics'],
                'reporting': [i for i in report.issues if i.category == 'reporting'],
            },
            'issues': [
                {
                    'category': i.category,
                    'severity': i.severity,
                    'description': i.description,
                    'suggestion': i.suggestion,
                    'section': i.section
                }
                for i in report.issues
            ]
        }


if __name__ == "__main__":
    from paper_parser import PaperParser

    sample_text = """
    Study on Exercise and Mental Health
    Authors: A. Smith, B. Jones

    Abstract
    We studied the effect of exercise on anxiety in adults.

    Methods
    Participants completed questionnaires before and after an 8-week exercise program.
    We randomly assigned participants to exercise or control conditions.
    The study was approved by the IRB (Protocol #2024-001).
    Informed consent was obtained from all participants.

    Results
    The exercise group showed improvement. t(48) = 3.21, p = 0.002.
    Effect size: Cohen's d = 0.89.

    Conflict of Interest: The authors declare no conflict of interest.
    Funded by: National Science Foundation grant #12345.
    """

    parser = PaperParser()
    paper = parser.parse_text(sample_text, "Exercise Mental Health Study")

    validator = ExperimentValidator()
    report = validator.validate(paper)
    summary = validator.get_summary(report)

    print(f"Design Score: {summary['design_score']:.1f}/100")
    print(f"Reproducibility Score: {summary['reproducibility_score']:.1f}/100")
    print(f"Transparency Score: {summary['transparency_score']:.1f}/100")
    print(f"Overall: {summary['overall_score']:.1f}/100")
    print("\nChecklist:")
    for k, v in summary['checklist'].items():
        print(f"  {k}: {v}")
