"""ML Model 2: Multinomial Naive Bayes resume category classifier.

PURE PYTHON, explainable. No sklearn.

What it does:
  Resume text -> predicted category: BACKEND / DATA / FRONTEND / DEVOPS
  plus a confidence % for every category.

How Naive Bayes works (the interview answer):
  1. TRAINING: we show the model small labelled examples per category.
     It counts how often each word appears in each category.
     P(word | category) = (count of word in category + 1) / (total words in category + vocab size)
     The +1 is Laplace smoothing, so an unseen word never makes probability 0.
  2. PREDICTION (Bayes theorem): for a new resume, for each category:
     log_score(category) = log P(category) + sum of log P(word | category) for every word
     We add LOGS instead of multiplying tiny probabilities (they would underflow to 0).
  3. The category with the highest log_score wins. Softmax over the
     log_scores turns them into confidence % that add up to 100.
"""
import math
from collections import Counter, defaultdict

from app.scoring import tokenize

TRAINING_DATA: list[tuple[str, str]] = [
    ("python fastapi rest api postgresql database jwt authentication backend server", "BACKEND"),
    ("java spring boot microservices rest api mysql backend server endpoints", "BACKEND"),
    ("node express api mongodb backend authentication server database crud", "BACKEND"),
    ("python django flask api postgresql backend orm sql queries server", "BACKEND"),
    ("golang api microservices backend grpc server postgresql redis", "BACKEND"),
    ("fastapi pydantic sqlalchemy api backend python docker endpoints testing", "BACKEND"),
    ("python pandas numpy data analysis machine learning model training dataset", "DATA"),
    ("sql data warehouse etl pipeline analytics dashboard reporting python", "DATA"),
    ("machine learning deep learning tensorflow pytorch nlp data model", "DATA"),
    ("data science statistics python sklearn regression classification dataset features", "DATA"),
    ("spark hadoop big data etl pipeline warehouse analytics sql", "DATA"),
    ("power bi tableau data visualization analytics sql excel reporting", "DATA"),
    ("javascript react html css frontend ui components responsive design", "FRONTEND"),
    ("react typescript redux frontend state management ui hooks components", "FRONTEND"),
    ("angular javascript html css frontend web design responsive ui", "FRONTEND"),
    ("vue javascript frontend ui css html components web application", "FRONTEND"),
    ("html css javascript frontend design figma ui ux responsive layout", "FRONTEND"),
    ("react nextjs typescript frontend server components css tailwind ui", "FRONTEND"),
    ("aws docker kubernetes ci cd devops deployment cloud infrastructure terraform", "DEVOPS"),
    ("linux docker jenkins pipeline devops automation cloud aws deployment", "DEVOPS"),
    ("kubernetes helm docker containers devops monitoring prometheus grafana cloud", "DEVOPS"),
    ("terraform ansible infrastructure cloud aws azure devops automation provisioning", "DEVOPS"),
    ("ci cd github actions docker deployment devops linux shell scripting", "DEVOPS"),
    ("aws ec2 s3 lambda cloud devops infrastructure networking security deployment", "DEVOPS"),
]

CATEGORIES = ["BACKEND", "DATA", "FRONTEND", "DEVOPS"]


class NaiveBayesClassifier:
    """Multinomial Naive Bayes over word counts, trained once at startup."""

    def __init__(self, training_data: list[tuple[str, str]]):
        self.word_counts: dict[str, Counter] = defaultdict(Counter)
        self.total_words: Counter = Counter()
        self.doc_counts: Counter = Counter()
        vocab: set[str] = set()
        for text, label in training_data:
            tokens = tokenize(text)
            self.doc_counts[label] += 1
            for w in tokens:
                self.word_counts[label][w] += 1
                self.total_words[label] += 1
                vocab.add(w)
        self.vocab_size = len(vocab)
        self.total_docs = sum(self.doc_counts.values())

    def _log_score(self, tokens: list[str], label: str) -> float:
        score = math.log(self.doc_counts[label] / self.total_docs)
        denom = self.total_words[label] + self.vocab_size
        counts = self.word_counts[label]
        for w in tokens:
            score += math.log((counts.get(w, 0) + 1) / denom)
        return score

    def predict(self, text: str) -> dict:
        tokens = tokenize(text or "")
        if not tokens:
            return {"category": "UNKNOWN", "confidence": 0.0,
                    "scores": {c: 0.0 for c in CATEGORIES}}
        log_scores = {c: self._log_score(tokens, c) for c in CATEGORIES}
        m = max(log_scores.values())
        exps = {c: math.exp(s - m) for c, s in log_scores.items()}
        total = sum(exps.values())
        scores = {c: round(v / total * 100, 2) for c, v in exps.items()}
        best = max(scores, key=scores.get)
        return {"category": best, "confidence": scores[best], "scores": scores}


MODEL = NaiveBayesClassifier(TRAINING_DATA)


def classify_resume(text: str) -> dict:
    """Predict the category of one resume text."""
    return MODEL.predict(text)
