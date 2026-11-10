
import re
from difflib import SequenceMatcher
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# --------------------------------
# SENTENCE EXTRACTION
# --------------------------------

def split_sentences(text):

    sentences = re.split(
        r'(?<=[.!?])\s+|\n+',
        text
    )

    return [
        s.strip() for s in sentences
        if len(s.strip()) > 3
    ]


# --------------------------------
# CHANGE CLASSIFICATION
# --------------------------------

CATEGORIES = {
    "Security": [
        "security", "password", "access",
        "authentication", "breach", "encryption",
        "unauthorized", "confidential", "firewall"
    ],

    "Human Resources": [
        "employee", "salary", "attendance",
        "leave", "recruitment", "staff",
        "working hours", "termination"
    ],

    "Finance": [
        "budget", "payment", "invoice",
        "tax", "financial", "cost",
        "expense", "revenue"
    ],

    "Operations": [
        "workflow", "production", "delivery",
        "process", "operations", "approval"
    ],

    "Technology": [
        "software", "database", "server",
        "network", "system", "application",
        "infrastructure", "api"
    ],

    "Legal & Compliance": [
        "compliance", "contract", "regulation",
        "legal", "agreement", "audit",
        "privacy", "gdpr"
    ]
}


def classify_change(text):

    text = text.lower()

    scores = {}

    for category, keywords in CATEGORIES.items():

        score = sum(
            text.count(keyword)
            for keyword in keywords
        )

        if score > 0:
            scores[category] = score

    return scores


# --------------------------------
# SEMANTIC DOCUMENT COMPARISON
# --------------------------------

def semantic_comparison(old_text, new_text):

    old_sentences = split_sentences(old_text)
    new_sentences = split_sentences(new_text)

    if not old_sentences or not new_sentences:

        return {
            "added": new_sentences,
            "removed": old_sentences,
            "modified": [],
            "similarity": 0
        }

    all_sentences = old_sentences + new_sentences

    try:

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True
        )

        vectors = vectorizer.fit_transform(all_sentences)

        old_vectors = vectors[:len(old_sentences)]
        new_vectors = vectors[len(old_sentences):]

        similarity_matrix = cosine_similarity(
            old_vectors, new_vectors
        )

    except ValueError:

        similarity_matrix = [
            [
                SequenceMatcher(None, old, new).ratio()
                for new in new_sentences
            ]
            for old in old_sentences
        ]

    matched_old = set()
    matched_new = set()
    modified = []

    # Match the most similar sentences

    candidates = []

    for i in range(len(old_sentences)):
        for j in range(len(new_sentences)):

            score = float(similarity_matrix[i][j])

            if score >= 0.35:
                candidates.append((score, i, j))

    candidates.sort(reverse=True)

    for score, i, j in candidates:

        if i in matched_old or j in matched_new:
            continue

        matched_old.add(i)
        matched_new.add(j)

        if score < 0.95:

            modified.append({
                "old": old_sentences[i],
                "new": new_sentences[j],
                "similarity": round(score * 100, 2)
            })

    removed = [
        old_sentences[i]
        for i in range(len(old_sentences))
        if i not in matched_old
    ]

    added = [
        new_sentences[j]
        for j in range(len(new_sentences))
        if j not in matched_new
    ]

    similarity = SequenceMatcher(
        None, old_text, new_text
    ).ratio()

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "similarity": round(similarity * 100, 2)
    }


# --------------------------------
# RISK INTELLIGENCE
# --------------------------------

def calculate_risk(changes, categories):

    text = " ".join(
        changes["added"] +
        changes["removed"] +
        [
            item["old"] + " " + item["new"]
            for item in changes["modified"]
        ]
    ).lower()

    critical_terms = [
        "data breach", "unauthorized access",
        "data loss", "security breach",
        "confidential information",
        "legal penalty", "critical failure"
    ]

    high_terms = [
        "password", "security", "termination",
        "compliance violation", "encryption",
        "financial penalty", "privacy"
    ]

    medium_terms = [
        "salary", "attendance", "approval",
        "workflow", "database", "policy",
        "employee", "payment"
    ]

    score = 0

    critical_matches = [
        term for term in critical_terms
        if term in text
    ]

    high_matches = [
        term for term in high_terms
        if term in text
    ]

    medium_matches = [
        term for term in medium_terms
        if term in text
    ]

    score += len(critical_matches) * 30
    score += len(high_matches) * 15
    score += len(medium_matches) * 8

    total_changes = (
        len(changes["added"]) +
        len(changes["removed"]) +
        len(changes["modified"])
    )

    score += min(total_changes * 3, 20)
    score += min(len(categories) * 3, 15)

    score = min(score, 100)

    if critical_matches or score >= 70:
        level = "Critical"
    elif score >= 40:
        level = "High"
    elif score >= 20:
        level = "Medium"
    else:
        level = "Low"

    return {
        "score": score,
        "level": level,
        "critical_matches": critical_matches,
        "high_matches": high_matches,
        "medium_matches": medium_matches
    }


# --------------------------------
# DEPARTMENT IMPACT
# --------------------------------

DEPARTMENT_MAP = {
    "Security": "Information Technology",
    "Human Resources": "Human Resources",
    "Finance": "Finance",
    "Operations": "Operations",
    "Technology": "Information Technology",
    "Legal & Compliance": "Legal & Compliance"
}


def predict_impact(categories):

    departments = []

    for category in categories:

        department = DEPARTMENT_MAP.get(category)

        if department and department not in departments:
            departments.append(department)

    return departments or ["Manual Review Required"]


# --------------------------------
# RECOMMENDATION ENGINE
# --------------------------------

def generate_recommendations(risk, categories):

    recommendations = []

    if risk["level"] in ["Critical", "High"]:

        recommendations.append(
            "Escalate this change for immediate management review."
        )

    if "Security" in categories:

        recommendations.append(
            "Conduct a security assessment and validate access controls."
        )

    if "Human Resources" in categories:

        recommendations.append(
            "Notify affected employees and update HR documentation."
        )

    if "Finance" in categories:

        recommendations.append(
            "Review budget implications and financial approvals."
        )

    if "Technology" in categories:

        recommendations.append(
            "Perform compatibility testing and validate system dependencies."
        )

    if "Operations" in categories:

        recommendations.append(
            "Review operational workflows and prepare an implementation plan."
        )

    if "Legal & Compliance" in categories:

        recommendations.append(
            "Obtain a compliance review before implementing the change."
        )

    if not recommendations:

        recommendations.append(
            "Conduct a manual review and obtain stakeholder approval."
        )

    return recommendations


# --------------------------------
# MAIN AI IMPACT ANALYSIS
# --------------------------------

def analyze_impact(old_text, new_text):

    changes = semantic_comparison(
        old_text,
        new_text
    )

    changed_content = " ".join(
        changes["added"] +
        changes["removed"] +
        [
            item["old"] + " " + item["new"]
            for item in changes["modified"]
        ]
    )

    categories = classify_change(changed_content)

    risk = calculate_risk(
        changes,
        categories
    )

    departments = predict_impact(
        categories
    )

    recommendations = generate_recommendations(
        risk,
        categories
    )

    if risk["level"] == "Critical":
        summary = (
            "Critical changes detected. Immediate management "
            "and specialist review is recommended."
        )

    elif risk["level"] == "High":
        summary = (
            "Significant business changes detected. "
            "Affected teams should review implementation risks."
        )

    elif risk["level"] == "Medium":
        summary = (
            "Moderate changes detected. Department-level "
            "validation is recommended."
        )

    else:
        summary = (
            "Low-risk changes detected. Routine verification "
            "and monitoring are recommended."
        )

    return {
        "success": True,
        "similarity": changes["similarity"],
        "changes": changes,
        "categories": categories,
        "risk": risk,
        "departments": departments,
        "recommendations": recommendations,
        "summary": summary,
        "engine": "Local NLP + TF-IDF Intelligence Engine"
    }
