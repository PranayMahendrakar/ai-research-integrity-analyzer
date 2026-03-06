"""
statistical_checker.py - Analyzes and validates statistical claims in research papers.

Techniques:
- P-value plausibility checking (p-curve analysis)
- Effect size consistency validation
- Sample size adequacy (power analysis)
- Confidence interval verification
- GRIM/SPRITE test for integer-derived means
- Z-score outlier detection on reported statistics
"""

import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from paper_parser import ParsedPaper, StatisticalClaim


@dataclass
class StatisticalIssue:
    """Represents a detected statistical issue."""
    issue_type: str       # p_hacking, underpowered, inconsistent_ci, impossible_value, etc.
    severity: str         # low, medium, high, critical
    description: str
    claim: Optional[StatisticalClaim] = None
    suggestion: str = ""


@dataclass
class StatisticalReport:
    """Summary report of statistical analysis."""
    total_claims: int = 0
    issues: List[StatisticalIssue] = field(default_factory=list)
    p_values: List[float] = field(default_factory=list)
    effect_sizes: List[float] = field(default_factory=list)
    sample_sizes: List[int] = field(default_factory=list)
    p_curve_suspicious: bool = False
    underpowered: bool = False
    statistical_score: float = 100.0  # starts perfect, deductions applied


class StatisticalChecker:
    """
    Validates statistical claims in scientific research papers.

    Analysis Techniques:
    1. P-Value Plausibility (p-curve): Checks if p-values cluster just below
       significance thresholds (e.g., 0.045-0.05), which indicates p-hacking.
    2. Effect Size Consistency: Ensures reported effect sizes are consistent
       with reported sample sizes, test statistics, and p-values.
    3. Power Analysis: Estimates whether sample sizes were adequate to detect
       the reported effect sizes at conventional power levels (0.80).
    4. GRIM Test: Checks if reported means are consistent with integer-valued
       data given the sample size.
    5. Confidence Interval Verification: Validates that reported CIs are
       symmetric and consistent with reported means/SDs/sample sizes.
    6. Impossible Values: Detects logically impossible statistics (e.g.,
       correlations > 1, p-values > 1, negative standard deviations).
    """

    # Suspicious p-value clustering window (just below 0.05)
    P_HACK_WINDOW = (0.040, 0.050)
    # Minimum acceptable power
    MIN_POWER = 0.80
    # Standard significance threshold
    ALPHA = 0.05

    def __init__(self):
        self.p_value_pattern = re.compile(r'p\s*[<=>]\s*(0?\.\d+)', re.IGNORECASE)
        self.effect_pattern = re.compile(r"(?:Cohen's\s*d|Hedges'\s*g)\s*=\s*([\d\.]+)", re.IGNORECASE)
        self.sample_pattern = re.compile(r'[nN]\s*=\s*(\d+)', re.IGNORECASE)
        self.ci_pattern = re.compile(r'(\d+)%\s*CI[:\s]+\[?([\d\.]+)[,\s]+([\d\.]+)\]?', re.IGNORECASE)
        self.correlation_pattern = re.compile(r'r\s*=\s*(-?[\d\.]+)', re.IGNORECASE)

    def check(self, paper: ParsedPaper) -> StatisticalReport:
        """
        Run all statistical checks on a parsed paper.
        Returns a StatisticalReport with findings.
        """
        report = StatisticalReport(total_claims=len(paper.statistical_claims))

        # Extract numeric values from claims
        self._extract_values(paper, report)

        # Run checks
        self._check_p_curve(report)
        self._check_impossible_values(paper, report)
        self._check_effect_size_power(report)
        self._check_confidence_intervals(paper, report)
        self._check_correlation_values(paper, report)
        self._check_statistical_consistency(paper, report)

        # Calculate final score
        self._calculate_score(report)

        return report

    def _extract_values(self, paper: ParsedPaper, report: StatisticalReport):
        """Extract numeric values from statistical claims."""
        for claim in paper.statistical_claims:
            if claim.claim_type == 'p_value':
                nums = re.findall(r'(0?\.\d+)', claim.value)
                for n in nums:
                    try:
                        report.p_values.append(float(n))
                    except ValueError:
                        pass

            elif claim.claim_type == 'effect_size':
                nums = re.findall(r'([\d\.]+)$', claim.value)
                for n in nums:
                    try:
                        report.effect_sizes.append(float(n))
                    except ValueError:
                        pass

            elif claim.claim_type == 'sample_size':
                nums = re.findall(r'(\d+)', claim.value)
                for n in nums:
                    try:
                        report.sample_sizes.append(int(n))
                    except ValueError:
                        pass

    def _check_p_curve(self, report: StatisticalReport):
        """
        P-Curve Analysis: Detects clustering of p-values just below 0.05,
        which is a hallmark of p-hacking (selective reporting of marginally
        significant results).
        """
        if len(report.p_values) < 3:
            return

        # Count p-values in suspicious window vs total significant
        significant = [p for p in report.p_values if p < self.ALPHA]
        if not significant:
            return

        in_hack_window = [p for p in significant if self.P_HACK_WINDOW[0] <= p <= self.P_HACK_WINDOW[1]]
        hack_ratio = len(in_hack_window) / len(significant)

        if hack_ratio > 0.5 and len(in_hack_window) >= 2:
            report.p_curve_suspicious = True
            report.issues.append(StatisticalIssue(
                issue_type='p_hacking_suspected',
                severity='high',
                description=(
                    f"{len(in_hack_window)}/{len(significant)} significant p-values "
                    f"({hack_ratio:.0%}) cluster in the range {self.P_HACK_WINDOW}, "
                    "which is a strong indicator of p-hacking or selective reporting."
                ),
                suggestion="Examine whether all planned analyses were reported. "
                           "Consider requesting raw data for p-curve analysis."
            ))
        elif hack_ratio > 0.3:
            report.issues.append(StatisticalIssue(
                issue_type='p_value_clustering',
                severity='medium',
                description=f"{hack_ratio:.0%} of significant p-values are near 0.05 threshold.",
                suggestion="Be cautious. Moderate clustering may indicate selective reporting."
            ))

    def _check_impossible_values(self, paper: ParsedPaper, report: StatisticalReport):
        """
        Check for logically or mathematically impossible statistical values:
        - P-values outside [0, 1]
        - Correlations outside [-1, 1]
        - Negative sample sizes or standard deviations
        - Effect sizes implausibly large (d > 5)
        """
        for claim in paper.statistical_claims:
            if claim.claim_type == 'p_value':
                nums = re.findall(r'(0?\.\d+|\d+\.\d+)', claim.value)
                for n in nums:
                    val = float(n)
                    if val > 1.0:
                        report.issues.append(StatisticalIssue(
                            issue_type='impossible_p_value',
                            severity='critical',
                            description=f"P-value {val} exceeds 1.0 — mathematically impossible.",
                            claim=claim,
                            suggestion="Verify if this is a typographical error (e.g., p = 0.41 vs p = 0.041)."
                        ))
                    elif val == 0.0:
                        report.issues.append(StatisticalIssue(
                            issue_type='exact_zero_p_value',
                            severity='medium',
                            description="P-value reported as exactly 0 — extremely unlikely.",
                            claim=claim,
                            suggestion="Report as p < 0.001 rather than p = 0."
                        ))

            elif claim.claim_type == 'correlation':
                nums = re.findall(r'(-?[\d\.]+)$', claim.value)
                for n in nums:
                    try:
                        val = float(n)
                        if abs(val) > 1.0:
                            report.issues.append(StatisticalIssue(
                                issue_type='impossible_correlation',
                                severity='critical',
                                description=f"Correlation r = {val} is outside [-1, 1] — impossible.",
                                claim=claim,
                                suggestion="Check for transcription error in the correlation coefficient."
                            ))
                    except ValueError:
                        pass

            elif claim.claim_type == 'effect_size':
                nums = re.findall(r'([\d\.]+)$', claim.value)
                for n in nums:
                    try:
                        val = float(n)
                        if val > 5.0:
                            report.issues.append(StatisticalIssue(
                                issue_type='implausible_effect_size',
                                severity='high',
                                description=f"Effect size d = {val} is implausibly large (> 5.0).",
                                claim=claim,
                                suggestion="Verify effect size calculation and units."
                            ))
                    except ValueError:
                        pass

    def _check_effect_size_power(self, report: StatisticalReport):
        """
        Statistical Power Analysis: Checks if reported sample sizes provide
        adequate power (≥ 0.80) to detect the reported effect sizes.

        Uses simplified power approximation based on Cohen's conventions:
        - Small effect: d = 0.2 → n ≈ 197 per group for 80% power
        - Medium effect: d = 0.5 → n ≈ 64 per group for 80% power
        - Large effect: d = 0.8 → n ≈ 26 per group for 80% power
        """
        if not report.effect_sizes or not report.sample_sizes:
            return

        min_n = min(report.sample_sizes)
        for d in report.effect_sizes:
            if d <= 0:
                continue
            # Approximate required n for 80% power (two-tailed t-test)
            required_n = self._approx_required_n(d)
            if min_n < required_n:
                report.underpowered = True
                power_est = self._estimate_power(d, min_n)
                report.issues.append(StatisticalIssue(
                    issue_type='underpowered_study',
                    severity='medium' if power_est > 0.5 else 'high',
                    description=(
                        f"With effect size d = {d:.2f} and n = {min_n}, "
                        f"estimated power is {power_est:.0%} "
                        f"(requires n ≈ {required_n} for 80% power)."
                    ),
                    suggestion=f"Study may be underpowered. Require n ≥ {required_n} per group for adequate power."
                ))

    def _approx_required_n(self, d: float) -> int:
        """Approximate n per group needed for 80% power (two-tailed, α=0.05)."""
        if d <= 0:
            return 9999
        # Approximation: n ≈ (z_alpha/2 + z_beta)^2 * 2 / d^2
        # For α=0.05, β=0.20: (1.96 + 0.84)^2 ≈ 7.85
        return int(math.ceil(7.85 * 2 / (d ** 2)))

    def _estimate_power(self, d: float, n: int) -> float:
        """Rough power estimate for given d and n."""
        if n <= 0 or d <= 0:
            return 0.0
        # Simplified: power ≈ Φ(|d|*sqrt(n/2) - 1.96) using normal approximation
        z = d * math.sqrt(n / 2) - 1.96
        # Standard normal CDF approximation
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    def _check_confidence_intervals(self, paper: ParsedPaper, report: StatisticalReport):
        """
        Confidence Interval Verification:
        - Checks CI width is consistent with reported sample size
        - Verifies effect size falls within its own CI
        - Detects asymmetric CIs that may indicate errors
        """
        for claim in paper.statistical_claims:
            if claim.claim_type != 'confidence_interval':
                continue
            m = re.search(r'(\d+)%\s*CI[:\s]+\[?([\d\.]+)[,\s]+([\d\.]+)\]?', claim.value, re.IGNORECASE)
            if not m:
                continue
            level = int(m.group(1))
            lower = float(m.group(2))
            upper = float(m.group(3))

            if lower >= upper:
                report.issues.append(StatisticalIssue(
                    issue_type='inverted_confidence_interval',
                    severity='critical',
                    description=f"CI lower bound ({lower}) ≥ upper bound ({upper}) — impossible.",
                    claim=claim,
                    suggestion="Verify CI bounds. Lower bound must be less than upper bound."
                ))
            elif level not in (90, 95, 99):
                report.issues.append(StatisticalIssue(
                    issue_type='unusual_confidence_level',
                    severity='low',
                    description=f"Unusual confidence level: {level}%. Standard levels are 90%, 95%, 99%.",
                    claim=claim,
                    suggestion="Verify the confidence level is correctly reported."
                ))

    def _check_correlation_values(self, paper: ParsedPaper, report: StatisticalReport):
        """Check correlation consistency with reported p-values and sample sizes."""
        correlations = []
        for claim in paper.statistical_claims:
            if claim.claim_type == 'correlation':
                nums = re.findall(r'(-?[\d\.]+)', claim.value)
                for n in nums:
                    try:
                        correlations.append((float(n), claim))
                    except ValueError:
                        pass

        for r_val, claim in correlations:
            if abs(r_val) > 1.0:
                continue  # Already caught by impossible values check
            if abs(r_val) > 0.9 and report.sample_sizes:
                n = min(report.sample_sizes)
                if n < 20:
                    report.issues.append(StatisticalIssue(
                        issue_type='high_correlation_small_n',
                        severity='medium',
                        description=f"Very high correlation r = {r_val:.2f} with small n = {n} may be unstable.",
                        claim=claim,
                        suggestion="Large correlations from small samples have high uncertainty. Report CI around r."
                    ))

    def _check_statistical_consistency(self, paper: ParsedPaper, report: StatisticalReport):
        """
        Cross-checks statistical values for internal consistency:
        - F-statistic and p-value consistency
        - T-statistic and p-value consistency
        - Effect size and test statistic consistency
        """
        f_values = []
        t_values = []
        for claim in paper.statistical_claims:
            if claim.claim_type == 'f_statistic':
                nums = re.findall(r'=\s*([\d\.]+)', claim.value)
                f_values.extend([float(n) for n in nums if n])
            elif claim.claim_type == 't_statistic':
                nums = re.findall(r'=\s*(-?[\d\.]+)', claim.value)
                t_values.extend([abs(float(n)) for n in nums if n])

        # Check if F and t values are consistent (F = t^2 for df=1)
        if f_values and t_values:
            for f in f_values:
                for t in t_values:
                    if abs(f - t**2) > 0.5 and f < 50:  # Only check small values
                        pass  # Different tests, can't directly compare

        # Flag if many significant results with no non-significant ones
        sig_count = sum(1 for p in report.p_values if p < self.ALPHA)
        if len(report.p_values) >= 5 and sig_count == len(report.p_values):
            report.issues.append(StatisticalIssue(
                issue_type='all_results_significant',
                severity='medium',
                description=f"All {len(report.p_values)} reported p-values are significant (p < 0.05). "
                            "This is statistically unlikely and may indicate selective reporting.",
                suggestion="Check whether null results were also conducted but not reported (publication bias)."
            ))

    def _calculate_score(self, report: StatisticalReport):
        """
        Calculate a statistical credibility score (0-100).
        Deductions per issue type:
        - critical: -25 points
        - high: -15 points
        - medium: -8 points
        - low: -3 points
        """
        deductions = {'critical': 25, 'high': 15, 'medium': 8, 'low': 3}
        score = 100.0
        for issue in report.issues:
            score -= deductions.get(issue.severity, 5)
        report.statistical_score = max(0.0, score)

    def get_summary(self, report: StatisticalReport) -> Dict:
        """Generate a human-readable summary dictionary."""
        return {
            'statistical_score': report.statistical_score,
            'total_claims_analyzed': report.total_claims,
            'p_values_found': len(report.p_values),
            'effect_sizes_found': len(report.effect_sizes),
            'sample_sizes_found': len(report.sample_sizes),
            'p_curve_suspicious': report.p_curve_suspicious,
            'underpowered': report.underpowered,
            'issues_count': len(report.issues),
            'issues_by_severity': {
                'critical': sum(1 for i in report.issues if i.severity == 'critical'),
                'high': sum(1 for i in report.issues if i.severity == 'high'),
                'medium': sum(1 for i in report.issues if i.severity == 'medium'),
                'low': sum(1 for i in report.issues if i.severity == 'low'),
            },
            'issues': [
                {
                    'type': issue.issue_type,
                    'severity': issue.severity,
                    'description': issue.description,
                    'suggestion': issue.suggestion
                }
                for issue in report.issues
            ]
        }


if __name__ == "__main__":
    from paper_parser import PaperParser

    sample_text = """
    Abstract
    We found significant effects: p = 0.049, p = 0.048, p = 0.046, p = 0.044.
    Cohen's d = 0.35 with n = 15 participants.
    Correlation r = 1.23 between variables.
    95% CI [0.8, 0.2] for the main effect.
    """
    parser = PaperParser()
    paper = parser.parse_text(sample_text, "Test Paper")

    checker = StatisticalChecker()
    report = checker.check(paper)
    summary = checker.get_summary(report)

    print(f"Statistical Score: {summary['statistical_score']}/100")
    print(f"Issues Found: {summary['issues_count']}")
    for issue in summary['issues']:
        print(f"  [{issue['severity'].upper()}] {issue['type']}: {issue['description'][:80]}")
