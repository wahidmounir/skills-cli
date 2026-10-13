"""Task-aware relevance matching and keyword search engine for skills-cli."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Sequence

from .parser import ParsedSkill

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "you", "your", "yours", "yourself", "yourselves", "please", "can", "could",
    "want", "need", "like", "using", "use", "make", "create", "build", "run", "do"
}


def tokenize(text: str) -> list[str]:
    """Tokenize string into lowercase alphanumeric words with morphological stems."""
    clean = re.findall(r"[a-zA-Z0-9_-]+", text.lower())
    tokens = []
    for word in clean:
        w = word.strip("-_")
        if len(w) >= 2 and w not in STOPWORDS:
            tokens.append(w)
            # Morphological stems
            if w.endswith("tion") and len(w) > 5:
                tokens.append(w[:-4])
                tokens.append(w[:-4] + "te")
            elif w.endswith("ies") and len(w) > 4:
                tokens.append(w[:-3] + "y")
            elif w.endswith("ing") and len(w) > 5:
                tokens.append(w[:-3])
            elif w.endswith("ed") and len(w) > 4:
                tokens.append(w[:-2])
            elif w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
                tokens.append(w[:-1])
    return tokens


@dataclass
class MatchResult:
    skill: ParsedSkill
    score: float
    confidence_pct: int
    matched_terms: list[str]
    matched_headings: list[str]
    recommended_action: str
    reasons: list[str]


class SkillMatcher:
    """Evaluates task queries against skills using weighted TF-IDF & structural signals."""

    def __init__(self, skills: Sequence[ParsedSkill]):
        self.skills = list(skills)
        self._doc_count = len(self.skills)
        self._doc_freq: dict[str, int] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build term frequency and inverse document frequency index."""
        term_docs: dict[str, set[str]] = {}
        for skill in self.skills:
            seen_terms: set[str] = set()
            # Ingest name, tags, description, headings, body
            text_corpus = f"{skill.meta.name} {' '.join(skill.meta.tags)} {skill.meta.description} " \
                          f"{' '.join(s.title for s in skill.sections)} {skill.full_text[:5000]}"
            for t in tokenize(text_corpus):
                seen_terms.add(t)

            for t in seen_terms:
                term_docs.setdefault(t, set()).add(skill.meta.name)

        for term, docs in term_docs.items():
            self._doc_freq[term] = len(docs)

    def _idf(self, term: str) -> float:
        """Calculate inverse document frequency."""
        df = self._doc_freq.get(term, 0)
        return math.log(1.0 + (self._doc_count - df + 0.5) / (df + 0.5))

    def match(self, query: str, limit: int = 5, min_score: float = 0.15) -> list[MatchResult]:
        """Rank skills matching a natural language task description."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        results: list[MatchResult] = []

        for skill in self.skills:
            score = 0.0
            matched_terms = set()
            matched_headings = []
            reasons = []

            skill_name_lower = skill.meta.name.lower()
            desc_tokens = set(tokenize(skill.meta.description))
            name_tokens = set(tokenize(skill.meta.name))
            tag_tokens = set(tokenize(" ".join(skill.meta.tags)))

            # Check direct name match
            if skill_name_lower in query.lower() or query.lower() in skill_name_lower:
                score += 15.0
                matched_terms.add(skill.meta.name)
                reasons.append(f"exact name match '{skill.meta.name}'")

            # Check heading matches
            for sec in skill.sections:
                sec_tokens = set(tokenize(sec.title))
                overlap = sec_tokens.intersection(query_tokens)
                if overlap:
                    score += 4.0 * len(overlap)
                    matched_headings.append(sec.title)
                    matched_terms.update(overlap)

            # Check token overlap in name, tags, description
            for t in query_tokens:
                idf = self._idf(t)
                if t in name_tokens:
                    score += 8.0 * idf
                    matched_terms.add(t)
                elif t in tag_tokens:
                    score += 6.0 * idf
                    matched_terms.add(t)
                elif t in desc_tokens:
                    score += 4.0 * idf
                    matched_terms.add(t)
                elif t in skill.full_text.lower():
                    # Term frequency in body
                    freq = min(skill.full_text.lower().count(t), 5)
                    score += (0.8 * freq) * idf
                    matched_terms.add(t)

            if score <= 0.0:
                continue

            # Normalized confidence calculation
            max_possible = max(1.0, len(query_tokens) * 12.0)
            confidence = min(99, max(5, int((score / max_possible) * 100)))

            if score >= min_score:
                if matched_headings:
                    best_sec = matched_headings[0]
                    rec = f"skills-cli load {skill.meta.name} --section \"{best_sec}\""
                elif skill.token_estimate > 2000:
                    rec = f"skills-cli info {skill.meta.name} (or --summary)"
                else:
                    rec = f"skills-cli load {skill.meta.name}"

                reasons_str = reasons or [f"matched: {', '.join(sorted(matched_terms)[:4])}"]

                results.append(
                    MatchResult(
                        skill=skill,
                        score=round(score, 2),
                        confidence_pct=confidence,
                        matched_terms=sorted(list(matched_terms)),
                        matched_headings=matched_headings[:3],
                        recommended_action=rec,
                        reasons=reasons_str,
                    )
                )

        # Sort descending by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
