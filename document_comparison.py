"""Offline comparison helpers for saved SOW IA documents."""
import re
import unicodedata
from collections import Counter

_STOP_WORDS = set("""
a au aux avec ce ces dans de des du elle en et eux il ils je la le les leur lui ma mais
me meme mes moi mon ne nos notre nous on ou par pas pour qu que quelle quelles qui sa
se ses son sur ta te tes toi ton tu un une vos votre vous the a an and are as at be by
for from in has have i in is it its of on or our that the their them there they this to
was we were will with you your
""".split())


def _tokens(text):
    normalized = unicodedata.normalize("NFD", str(text or "").casefold())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return re.findall(r"[a-z0-9]{3,}", normalized)


def compare_documents(documents, max_terms=12):
    """Compare 2–5 {title, extracted_text} documents without an external AI."""
    if not isinstance(documents, (list, tuple)) or not 2 <= len(documents) <= 5:
        raise ValueError("La comparaison nécessite entre 2 et 5 documents.")
    prepared = []
    for document in documents:
        title = str(document.get("title") or "Document")
        text = str(document.get("extracted_text") or "")
        if not text.strip():
            raise ValueError("Un document sélectionné ne contient pas de texte.")
        terms = [word for word in _tokens(text) if word not in _STOP_WORDS]
        counts = Counter(terms)
        prepared.append({"title": title, "counts": counts, "terms": set(counts)})
    common = set.intersection(*(item["terms"] for item in prepared))
    union = set.union(*(item["terms"] for item in prepared))
    common_ranked = sorted(common, key=lambda word: (-sum(item["counts"][word] for item in prepared), word))
    details = []
    for item in prepared:
        unique = item["terms"] - set.union(*(other["terms"] for other in prepared if other is not item))
        details.append({
            "title": item["title"],
            "distinctive_terms": sorted(unique, key=lambda word: (-item["counts"][word], word))[:max_terms],
            "term_count": len(item["terms"]),
        })
    return {
        "document_count": len(prepared),
        "shared_terms": common_ranked[:max_terms],
        "shared_term_count": len(common),
        "similarity_percent": round(100 * len(common) / len(union)) if union else 0,
        "documents": details,
    }

_NEGATIONS = {"aucun", "aucune", "jamais", "non", "pas", "sans", "ni", "n"}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")


def _sentence_facts(text):
    facts = []
    for sentence in _SENTENCE_SPLIT.split(str(text or "")):
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        tokens = [word for word in _tokens(sentence) if word not in _STOP_WORDS]
        anchors = set(tokens)
        if len(anchors) < 2:
            continue
        numbers = set(re.findall(r"(?<![a-z])\d+(?:[.,]\d+)?%?(?![a-z])", sentence.casefold()))
        polarity = any(word in _NEGATIONS for word in _tokens(sentence))
        facts.append({"sentence": sentence[:500], "anchors": anchors, "numbers": numbers, "polarity": polarity})
    return facts


def find_possible_differences(documents, max_pairs=20):
    """Flag candidate conflicts based on shared terms plus differing numbers or negation."""
    if not isinstance(documents, (list, tuple)) or not 2 <= len(documents) <= 5:
        raise ValueError("La comparaison nécessite entre 2 et 5 documents.")
    prepared = []
    for document in documents:
        text = str(document.get("extracted_text") or "")
        if not text.strip():
            raise ValueError("Un document sélectionné ne contient pas de texte.")
        prepared.append({
            "title": str(document.get("title") or "Document"),
            "facts": _sentence_facts(text),
        })
    candidates = []
    for left_index in range(len(prepared)):
        for right_index in range(left_index + 1, len(prepared)):
            left_doc, right_doc = prepared[left_index], prepared[right_index]
            for left in left_doc["facts"]:
                for right in right_doc["facts"]:
                    shared = left["anchors"] & right["anchors"]
                    if len(shared) < 2:
                        continue
                    reasons = []
                    if left["numbers"] and right["numbers"] and left["numbers"] != right["numbers"]:
                        reasons.append("valeurs numériques différentes")
                    if left["polarity"] != right["polarity"]:
                        reasons.append("formulation affirmative/négative différente")
                    if reasons:
                        candidates.append({
                            "document_a": left_doc["title"],
                            "excerpt_a": left["sentence"],
                            "document_b": right_doc["title"],
                            "excerpt_b": right["sentence"],
                            "shared_terms": sorted(shared)[:8],
                            "reasons": reasons,
                        })
                        if len(candidates) >= max_pairs:
                            return candidates
    return candidates
