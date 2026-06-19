"""
Synthetic-but-realistic dataset builder for TruthLens AI.

WHY THIS EXISTS
---------------
Public fake-news corpora (e.g. the Kaggle "Fake and Real News" dataset:
True.csv / Fake.csv) are large and licence-gated, so they cannot be bundled.
This module generates a balanced, linguistically realistic corpus so the
project trains and demos out-of-the-box, completely offline.

The generator injects cross-class overlap, shared neutral sentences and a small
fraction of ambiguous/mislabelled samples so the learned decision boundary is
non-trivial and the reported metrics are believable, not a misleading 100%.

To train on the FULL real dataset instead, drop `True.csv` and `Fake.csv`
into the /dataset folder; `load_real_kaggle_if_present()` will pick them up.
"""
from __future__ import annotations

import random

import pandas as pd

from . import config

SEED = config.RANDOM_STATE

# --------------------------------------------------------------------------- #
# Vocabulary pools
# --------------------------------------------------------------------------- #
TOPICS = ["the economy", "the new climate policy", "the national election",
          "the technology sector", "public health guidelines", "the stock market",
          "the education reform bill", "the space mission", "the infrastructure plan",
          "the cybersecurity report", "the energy transition", "the trade agreement"]

ORGS = ["the Reserve Bank", "the Health Ministry", "the World Bank",
        "the Election Commission", "Stanford University", "the European Commission",
        "the Department of Energy", "Reuters", "the Associated Press",
        "the National Statistics Office", "the Supreme Court", "NASA"]

PEOPLE = ["Dr. Anita Rao", "Minister Patel", "Governor Lee", "Professor Mehta",
          "spokesperson James Carter", "analyst Priya Sharma", "CEO Robert Kim",
          "researcher Elena Cruz", "official Mark Davis", "economist Sarah Quinn"]

NEUTRAL_VERBS = ["announced", "confirmed", "reported", "stated", "published",
                 "released data showing", "presented findings that", "clarified that"]

REAL_SENTENCES = [
    "According to {org}, {topic} grew by {n} percent in the last quarter.",
    "{person} {verb} that new measures regarding {topic} will take effect next month.",
    "Officials at {org} said the figures were based on data collected over {n} months.",
    "In a statement on {month} {day}, {person} described the changes to {topic} as gradual.",
    "{org} published a peer-reviewed report on {topic} citing {n} independent studies.",
    "Analysts noted that {topic} remained broadly stable, rising {n} percent year on year.",
    "{person} told {org} that the committee would review {topic} before the deadline.",
    "The report on {topic} included detailed methodology and was reviewed by {org}.",
    "Data from {org} indicated a {n} percent change in {topic} compared with last year.",
    "Speaking at a press conference, {person} addressed questions about {topic}.",
]

FAKE_SENTENCES = [
    "SHOCKING: They don't want you to know the TRUTH about {topic}!!!",
    "You won't believe what sources say is really happening with {topic}.",
    "BREAKING!! This one secret about {topic} will blow your mind - share before it's deleted!",
    "Experts claim {topic} is a complete hoax and the mainstream media is hiding it.",
    "People are saying {topic} is a cover-up orchestrated by powerful insiders.",
    "Doctors HATE this miracle trick that fixes {topic} overnight - wake up sheeple!",
    "Anonymous insiders reveal the forbidden truth about {topic} that was banned everywhere.",
    "The shocking secret behind {topic} that they tried to bury - do your own research!",
    "Rumors confirm {topic} is an explosive scandal nobody is talking about.",
    "This terrifying conspiracy about {topic} will destroy everything you thought you knew!!!",
]

HEADLINE_REAL = [
    "{org} releases quarterly update on {topic}",
    "{person} outlines new plan for {topic}",
    "Report examines impact of {topic} on local communities",
    "Committee reviews progress on {topic}",
]
HEADLINE_FAKE = [
    "THE SHOCKING TRUTH ABOUT {topic} THEY ARE HIDING",
    "You Won't BELIEVE What Just Happened With {topic}!!!",
    "EXPOSED: The Secret {topic} Cover-Up",
    "Doctors Are STUNNED By This {topic} Miracle",
]

# Neutral sentences shared by BOTH classes - genuine lexical overlap.
SHARED_SENTENCES = [
    "The story has attracted attention across social media this week.",
    "Officials have not commented on every aspect of {topic} so far.",
    "The development follows months of public discussion about {topic}.",
    "Readers have expressed a wide range of opinions about {topic}.",
    "Further updates on {topic} are expected in the coming days.",
    "The subject of {topic} has been widely shared online.",
    "Commentators continue to follow {topic} closely.",
    "{topic} remains a subject of ongoing debate among the public.",
    "Several outlets have covered {topic} over the past week.",
    "The article discusses recent events connected to {topic}.",
]

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def _fill(template: str, rng: random.Random) -> str:
    return template.format(
        topic=rng.choice(TOPICS),
        org=rng.choice(ORGS),
        person=rng.choice(PEOPLE),
        verb=rng.choice(NEUTRAL_VERBS),
        n=rng.randint(2, 48),
        month=rng.choice(MONTHS),
        day=rng.randint(1, 28),
    )


def _make_article(label: int, rng: random.Random) -> tuple[str, str]:
    """Return (title, text) for the given label, with realistic cross-class noise."""
    if label == config.LABEL_REAL:
        own, other, headlines = REAL_SENTENCES, FAKE_SENTENCES, HEADLINE_REAL
    else:
        own, other, headlines = FAKE_SENTENCES, REAL_SENTENCES, HEADLINE_FAKE

    n_sent = rng.randint(3, 6)
    sentences = [_fill(rng.choice(own), rng) for _ in range(n_sent)]

    for _ in range(rng.randint(1, 2)):
        sentences.append(_fill(rng.choice(SHARED_SENTENCES), rng))

    if rng.random() < 0.30:
        for _ in range(rng.randint(1, 2)):
            sentences.append(_fill(rng.choice(other), rng))
    elif rng.random() < 0.18:
        sentences.insert(rng.randrange(len(sentences)), _fill(rng.choice(other), rng))

    rng.shuffle(sentences)

    if rng.random() < 0.15:
        title = _fill(rng.choice(HEADLINE_FAKE if label == config.LABEL_REAL else HEADLINE_REAL), rng)
    else:
        title = _fill(rng.choice(headlines), rng)
    return title, " ".join(sentences)


def build_dataset(n_per_class: int = 1500, seed: int = SEED,
                  noise_rate: float = 0.05) -> pd.DataFrame:
    """
    Build a balanced labelled DataFrame: columns [title, text, label].

    `noise_rate` injects ambiguous/mislabelled samples to emulate the label
    noise present in real-world fake-news corpora, so metrics are realistic.
    """
    rng = random.Random(seed)
    rows = []
    for label in (config.LABEL_REAL, config.LABEL_FAKE):
        for _ in range(n_per_class):
            title, text = _make_article(label, rng)
            stored = label
            if rng.random() < noise_rate:
                stored = 1 - label
            rows.append({"title": title, "text": text, "label": stored})
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


def build_knowledge_base() -> pd.DataFrame:
    """A small corpus of verified reference statements for the fact-check agent."""
    facts = [
        ("economy", "Official GDP and inflation figures are published quarterly by national statistics offices and central banks."),
        ("economy", "Reputable economic reporting cites named institutions such as the Reserve Bank or the World Bank with dated figures."),
        ("climate", "Climate policy assessments are typically peer-reviewed and reference measurable emissions data over multiple years."),
        ("climate", "Claims that climate change is a 'hoax' contradict the consensus of peer-reviewed scientific literature."),
        ("election", "Official election results are certified by national election commissions, not by anonymous social-media sources."),
        ("election", "Credible election coverage attributes claims to named officials and verifiable records."),
        ("health", "Public-health guidance is issued by recognised health ministries and references clinical trial data."),
        ("health", "'Miracle cure' and 'doctors hate this trick' phrasing is a classic marker of health misinformation."),
        ("technology", "Technology-sector reporting from outlets like Reuters or the Associated Press cites company filings and named spokespeople."),
        ("science", "Scientific findings gain credibility when published in peer-reviewed journals with disclosed methodology."),
        ("stock market", "Stock-market movements are reported with specific index values and percentage changes from named exchanges."),
        ("general", "Vague sourcing such as 'people are saying' or 'sources say' without attribution is a hallmark of unreliable content."),
        ("general", "Excessive capitalisation, multiple exclamation marks, and urgency to 'share before it's deleted' indicate clickbait."),
        ("general", "Legitimate journalism includes dates, named sources, direct quotes, and verifiable statistics."),
        ("space", "Space-mission updates are released by agencies such as NASA with mission identifiers and telemetry data."),
        ("cybersecurity", "Cybersecurity advisories cite CVE identifiers, affected systems, and official vendor statements."),
        ("trade", "Trade-agreement reporting references signed documents, named negotiators, and ratification timelines."),
        ("education", "Education-reform reporting cites the text of the bill, named legislators, and implementation dates."),
    ]
    return pd.DataFrame(facts, columns=["topic", "statement"])


def load_real_kaggle_if_present():
    """Load the real Kaggle files (True.csv / Fake.csv) if present, else None."""
    true_p = config.DATASET_DIR / "True.csv"
    fake_p = config.DATASET_DIR / "Fake.csv"
    if true_p.exists() and fake_p.exists():
        real = pd.read_csv(true_p); fake = pd.read_csv(fake_p)
        real["label"] = config.LABEL_REAL; fake["label"] = config.LABEL_FAKE
        df = pd.concat([real, fake], ignore_index=True)
        for col in ("title", "text"):
            if col not in df.columns:
                df[col] = ""
        df = df[["title", "text", "label"]].dropna(subset=["text"])
        return df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    return None


def generate_and_save(n_per_class: int = 1500) -> dict:
    """Build all data files and persist them to the dataset folder."""
    config.DATASET_DIR.mkdir(parents=True, exist_ok=True)
    real = load_real_kaggle_if_present()
    df = real if real is not None else build_dataset(n_per_class=n_per_class)
    source = "Kaggle (True.csv/Fake.csv)" if real is not None else "synthetic-realistic generator"

    test = df.sample(frac=config.TEST_SIZE, random_state=SEED)
    train = df.drop(test.index)
    train.to_csv(config.TRAIN_CSV, index=False)
    test.to_csv(config.TEST_CSV, index=False)
    build_knowledge_base().to_csv(config.KNOWLEDGE_BASE_CSV, index=False)
    return {"source": source, "total": str(len(df)), "train": str(len(train)),
            "test": str(len(test)), "train_csv": str(config.TRAIN_CSV),
            "test_csv": str(config.TEST_CSV), "knowledge_base_csv": str(config.KNOWLEDGE_BASE_CSV)}


if __name__ == "__main__":
    for k, v in generate_and_save().items():
        print(f"{k:>20}: {v}")
