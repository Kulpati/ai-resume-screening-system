"""Explainable scoring: TF-IDF cosine similarity in PURE PYTHON + keywords.

No sklearn, no ML black box.
1. Tokenize: lowercase, keep words, drop stopwords / very short tokens.
2. Keywords = distinct meaningful words in the JD.
   matched = JD keywords present in the resume, missing = the rest.
3. TF-IDF: TF = how often a word appears in a doc, IDF = how rare it is
   across the corpus (JD + all resumes being screened). Rare, specific
   words (postgresql, fastapi) weigh more than common words.
4. Score = cosine similarity between JD vector and resume vector, x100.
"""
import math
import re
from collections import Counter

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with", "on", "at",
    "by", "is", "are", "was", "were", "be", "been", "will", "would", "should",
    "we", "you", "your", "our", "they", "their", "this", "that", "as", "from",
    "have", "has", "had", "who", "what", "when", "where", "how", "all", "any",
    "can", "could", "must", "should", "work", "working", "experience", "years",
    "year", "team", "role", "job", "candidate", "skills", "skill", "strong",
    "good", "looking", "join", "help", "using", "used", "use", "including",
    "etc", "plus", "ability", "knowledge", "familiarity", "required", "requirements",
    "need", "needs", "build", "builds", "building", "built", "uses", "include",
    "includes", "included", "including", "design", "designs", "backed",
}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    words = re.findall(r"[a-z][a-z0-9+#]*", text.lower())
    return [w for w in words if len(w) >= 2 and w not in STOPWORDS]


def extract_keywords(jd_text: str) -> list[str]:
    """Distinct meaningful JD words, in first-appearance order."""
    seen, out = set(), []
    for w in tokenize(jd_text):
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _tfidf_vector(tokens: list[str], vocab: list[str], idf: dict[str, float]) -> list[float]:
    counts = Counter(tokens)
    total = len(tokens) or 1
    return [(counts.get(word, 0) / total) * idf.get(word, 0.0) for word in vocab]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def score_resumes(jd_text: str, resume_texts: list[str]) -> list[dict]:
    """Score every resume against the JD. Returns one dict per resume."""
    keywords = extract_keywords(jd_text)
    jd_tokens = tokenize(jd_text)
    docs_tokens = [jd_tokens] + [tokenize(t) for t in resume_texts]

    # IDF over the whole corpus (JD + resumes)
    n = len(docs_tokens)
    idf = {}
    for word in keywords:
        df = sum(1 for tokens in docs_tokens if word in tokens)
        idf[word] = math.log((1 + n) / (1 + df)) + 1.0

    jd_vec = _tfidf_vector(jd_tokens, keywords, idf)
    results = []
    for text in resume_texts:
        tokens = tokenize(text)
        resume_vec = _tfidf_vector(tokens, keywords, idf)
        sim = _cosine(jd_vec, resume_vec)
        resume_set = set(tokens)
        matched = [k for k in keywords if k in resume_set]
        missing = [k for k in keywords if k not in resume_set]
        results.append({
            "score": round(max(0.0, min(100.0, sim * 100)), 2),
            "matched_keywords": matched,
            "missing_keywords": missing,
        })
    return results


def score_one(jd_text: str, resume_text: str) -> dict:
    return score_resumes(jd_text, [resume_text])[0]
