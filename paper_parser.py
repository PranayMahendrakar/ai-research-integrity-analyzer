"""
paper_parser.py - Parses scientific research papers to extract structured content.

Handles: PDF/text extraction, section identification, figure/table references,
citation parsing, and statistical value extraction.
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class PaperSection:
    """Represents a section of a research paper."""
    title: str
    content: str
    section_type: str  # abstract, introduction, methods, results, discussion, conclusion
    start_line: int = 0
    end_line: int = 0


@dataclass
class StatisticalClaim:
    """Represents a statistical claim found in the paper."""
    value: str
    context: str
    claim_type: str  # p_value, effect_size, sample_size, confidence_interval, correlation
    section: str
    line_number: int


@dataclass
class ParsedPaper:
    """Complete parsed representation of a research paper."""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    sections: List[PaperSection] = field(default_factory=list)
    statistical_claims: List[StatisticalClaim] = field(default_factory=list)
    figures: List[Dict] = field(default_factory=list)
    tables: List[Dict] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    raw_text: str = ""
    metadata: Dict = field(default_factory=dict)


class PaperParser:
    """
    Parses scientific research papers to extract structured information.

    Analysis Techniques:
    1. Section Detection: Uses regex patterns to identify standard paper sections.
    2. Statistical Pattern Matching: Identifies p-values, effect sizes, CIs, sample sizes.
    3. Figure/Table Extraction: Detects figure/table references and captions.
    4. Citation Parsing: Extracts in-text citations and reference lists.
    5. Keyword Extraction: Identifies author-supplied keywords.
    """

    SECTION_PATTERNS = {
        'abstract':     r'(?i)\b(abstract|summary)\b',
        'introduction': r'(?i)\b(introduction|background|overview)\b',
        'methods':      r'(?i)\b(methods?|methodology|materials?\s+and\s+methods?)\b',
        'results':      r'(?i)\b(results?|findings?|outcomes?)\b',
        'discussion':   r'(?i)\b(discussion|interpretation|implications?)\b',
        'conclusion':   r'(?i)\b(conclusions?|summary|final\s+remarks?)\b',
        'references':   r'(?i)\b(references?|bibliography|works\s+cited)\b',
    }

    STATISTICAL_PATTERNS = {
        'p_value':             r'p\s*[<=>]\s*0?\.\d+',
        'confidence_interval': r'\d+%\s*(?:CI|confidence\s+interval)[:\s]+\[?[\d\.]+[,\s]+[\d\.]+\]?',
        'effect_size':         r"(?:Cohen's\s*d|Hedges'\s*g|eta\s*squared)\s*=\s*[\d\.]+",
        'sample_size':         r'[nN]\s*=\s*\d+|sample\s+size(?:\s+of)?\s+\d+',
        'correlation':         r'r\s*=\s*-?[\d\.]+',
        'mean_sd':             r'(?:mean|M)\s*=\s*[\d\.]+\s*[\(,±]\s*(?:SD)?\s*=?\s*[\d\.]+',
        'f_statistic':         r'F\s*\([\d,\s]+\)\s*=\s*[\d\.]+',
        't_statistic':         r't\s*\([\d,\s]+\)\s*=\s*-?[\d\.]+',
        'chi_square':          r'chi.square\s*=\s*[\d\.]+',
    }

    def __init__(self):
        self.compiled_section_patterns = {k: re.compile(v) for k, v in self.SECTION_PATTERNS.items()}
        self.compiled_stat_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.STATISTICAL_PATTERNS.items()}

    def parse_text(self, text: str, title: str = "Unknown") -> ParsedPaper:
        """Parse raw text content of a research paper."""
        paper = ParsedPaper(title=title, raw_text=text)
        lines = text.split('\n')
        paper.title = self._extract_title(lines) or title
        paper.authors = self._extract_authors(lines)
        paper.abstract = self._extract_abstract(text)
        paper.keywords = self._extract_keywords(text)
        paper.sections = self._extract_sections(text, lines)
        paper.statistical_claims = self._extract_statistical_claims(text, lines)
        paper.figures = self._extract_figures(text)
        paper.tables = self._extract_tables(text)
        paper.references = self._extract_references(text)
        paper.metadata = self._extract_metadata(text)
        return paper

    def parse_json(self, json_data: dict) -> ParsedPaper:
        """Parse paper from a JSON structured format."""
        paper = ParsedPaper()
        paper.title = json_data.get('title', '')
        paper.authors = json_data.get('authors', [])
        paper.abstract = json_data.get('abstract', '')
        paper.keywords = json_data.get('keywords', [])
        raw_text = json_data.get('full_text', '')
        paper.raw_text = raw_text
        if raw_text:
            lines = raw_text.split('\n')
            paper.sections = self._extract_sections(raw_text, lines)
            paper.statistical_claims = self._extract_statistical_claims(raw_text, lines)
            paper.figures = self._extract_figures(raw_text)
            paper.tables = self._extract_tables(raw_text)
            paper.references = self._extract_references(raw_text)
        return paper

    def _extract_title(self, lines: List[str]) -> Optional[str]:
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 10 and not line.lower().startswith(('abstract', 'author', 'doi', 'http')):
                return line
        return None

    def _extract_authors(self, lines: List[str]) -> List[str]:
        author_pattern = re.compile(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)+)')
        for line in lines[1:15]:
            if author_pattern.match(line.strip()):
                return [p.strip() for p in line.split(',') if len(p.strip()) > 3]
        return []

    def _extract_abstract(self, text: str) -> str:
        pattern = re.compile(r'(?i)abstract[:\s]*\n+(.*?)(?=\n\n[A-Z]|\nKeywords|\nIntroduction)', re.DOTALL)
        m = pattern.search(text)
        return m.group(1).strip()[:2000] if m else ""

    def _extract_keywords(self, text: str) -> List[str]:
        m = re.search(r'(?i)keywords?[:\s]+(.*?)(?=\n\n|\nIntroduction)', text, re.DOTALL)
        if m:
            return [k.strip() for k in re.split(r'[,;]', m.group(1)) if k.strip()]
        return []

    def _extract_sections(self, text: str, lines: List[str]) -> List[PaperSection]:
        sections = []
        current = {'title': 'Preamble', 'type': 'preamble', 'start': 0, 'content': []}
        for i, line in enumerate(lines):
            detected = False
            for stype, pat in self.compiled_section_patterns.items():
                if len(line.strip()) < 80 and pat.search(line) and (line.isupper() or line.istitle()):
                    sections.append(PaperSection(
                        title=current['title'], content='\n'.join(current['content']),
                        section_type=current['type'], start_line=current['start'], end_line=i
                    ))
                    current = {'title': line.strip(), 'type': stype, 'start': i, 'content': []}
                    detected = True
                    break
            if not detected:
                current['content'].append(line)
        if current['content']:
            sections.append(PaperSection(
                title=current['title'], content='\n'.join(current['content']),
                section_type=current['type'], start_line=current['start'], end_line=len(lines)
            ))
        return sections

    def _extract_statistical_claims(self, text: str, lines: List[str]) -> List[StatisticalClaim]:
        claims = []
        current_section = 'unknown'
        for i, line in enumerate(lines):
            for stype, pat in self.compiled_section_patterns.items():
                if pat.search(line) and len(line.strip()) < 80:
                    current_section = stype
            for ctype, pat in self.compiled_stat_patterns.items():
                for match in pat.finditer(line):
                    ctx = ' '.join(lines[max(0, i-1):min(len(lines), i+2)]).strip()
                    claims.append(StatisticalClaim(
                        value=match.group(0), context=ctx[:300],
                        claim_type=ctype, section=current_section, line_number=i
                    ))
        return claims

    def _extract_figures(self, text: str) -> List[Dict]:
        return [{'reference': m.group(1), 'caption': m.group(2).strip()[:500]}
                for m in re.finditer(r'(?i)(Fig(?:ure)?\s*\.?\s*\d+)[:\s]+(.*?)(?=\n\n)', text, re.DOTALL)]

    def _extract_tables(self, text: str) -> List[Dict]:
        return [{'reference': m.group(1), 'caption': m.group(2).strip()[:500]}
                for m in re.finditer(r'(?i)(Table\s*\.?\s*\d+)[:\s]+(.*?)(?=\n\n)', text, re.DOTALL)]

    def _extract_references(self, text: str) -> List[str]:
        m = re.search(r'(?i)\breferences?\b.*?\n(.*?)$', text, re.DOTALL)
        if m:
            refs = re.split(r'\n(?=\[?\d+\]?\.?\s+[A-Z])', m.group(1))
            return [r.strip() for r in refs if len(r.strip()) > 20]
        return []

    def _extract_metadata(self, text: str) -> Dict:
        meta = {}
        doi = re.search(r'10\.\d{4,}/[\S]+', text)
        if doi:
            meta['doi'] = doi.group(0)
        year = re.findall(r'\b(19|20)\d{2}\b', text[:500])
        if year:
            meta['year'] = year[0]
        return meta

    def to_dict(self, paper: ParsedPaper) -> dict:
        return {
            'title': paper.title,
            'authors': paper.authors,
            'abstract': paper.abstract,
            'keywords': paper.keywords,
            'sections': [{'title': s.title, 'content': s.content[:1000], 'section_type': s.section_type} for s in paper.sections],
            'statistical_claims': [{'value': c.value, 'context': c.context, 'claim_type': c.claim_type, 'section': c.section} for c in paper.statistical_claims],
            'figures': paper.figures,
            'tables': paper.tables,
            'references_count': len(paper.references),
            'metadata': paper.metadata
        }


if __name__ == "__main__":
    sample = """
    Sleep Deprivation and Cognitive Performance: A Meta-Analysis
    John Smith, Jane Doe

    Abstract
    We analyzed 45 studies (N = 2847). Results: p < 0.001, Cohen's d = 0.73, 95% CI [0.58, 0.88].

    Keywords: sleep, cognition, meta-analysis

    Methods
    Sample size: n = 2847. Databases: PubMed, PsycINFO.

    Results
    Effect size: Cohen's d = 0.73. Correlation: r = 0.62. t(44) = 8.92.
    """
    parser = PaperParser()
    paper = parser.parse_text(sample, "Sleep Meta-Analysis")
    print(f"Title: {paper.title}")
    print(f"Statistical claims: {len(paper.statistical_claims)}")
    for c in paper.statistical_claims:
        print(f"  [{c.claim_type}] {c.value}")
