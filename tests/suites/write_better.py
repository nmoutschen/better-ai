"""Data for /write-better. Better writing means, in separate dimensions:

Scored on every rewrite:
- intro_states_point: the opening sentences state the main point, instead of announcing it.
- structure: the reader can find each part, in proportion to the text's length.
- no_expertise_pollution: the output gives its audience the context to understand all of it.
- reasoning: causes and logical links are stated.
- consistent_terms: each thing keeps one name throughout.
- stated_limits: uncertainty and disagreement in the original are kept and not overstated.
- literal_language: no metaphors, hints, or vague terms.
- neutral_tone: neither enthusiastic nor aggressive.
- restraint: the rewrite doesn't grow much beyond the original.
- no_invented_claims: nothing is added.

Scored only where the text helps a reader decide:
- decision_first: a decision gets its recommendation or criteria straight after the opening.

Scored where a case has known answers:
- reader_success: a reader of the output alone can get the right answer.
- limits_kept: a reader of the output alone also gets the limits and conditions on that answer.
- fidelity: the exact dates or prices that must survive are present. This is a pattern match. A
  judged version was removed because an exact copy of the original scored 0.58 to 0.91, and
  formatting alone moved the score by up to 0.32.

The main purpose is rewriting AI outputs for the user, so most cases invoke the skill alone on a
previous reply. Replies in tests/replies are frozen, non-coding AI answers, so scores stay comparable
between skill versions. Don't read the holdout-* outputs while changing the skill.
Two cases invoke it with a text.
"""

from pathlib import Path

from harness import (
    Bound,
    Damage,
    Effect,
    Judged,
    Matches,
    ReaderAnswers,
    SkillEval,
    add_opening,
    add_text,
    flatten_text,
    replace_output,
    reverse_sentences,
)


def expertise_check(audience: str) -> Judged:
    # This can't see the original, which could supply context that the output leaves out.
    return Judged(
        "no_expertise_pollution",
        f"The reader is {audience} Does this text give them the context to understand everything "
        "it says, with no unexplained names, terms, or references?",
        sees_task=False,
    )


GENERAL_READER = expertise_check("an adult with no specialist knowledge of the subject.")


SHARED_CHECKS = (
    Judged(
        "no_invented_claims",
        "Is every factual claim in the output also in the document in the task? Score Not met if "
        "even one claim is missing from the document. An example that only illustrates a concept "
        "does not count as a claim.",
    ),
    Judged(
        "stated_limits",
        "Does the output keep the uncertainty, limits, and disagreement in the document, without "
        "sounding more certain than the document does?",
    ),
    # These are about the text itself, so the original must not fill any gaps.
    Judged(
        "structure",
        "Can a reader find each part of this text without reading all of it, using structure in "
        "proportion to its length? A very short text needs no headings.",
        sees_task=False,
    ),
    Judged(
        "reasoning",
        "Does this text state why things follow from each other, with its causes and logical links "
        "spelled out and in a sensible order?",
        sees_task=False,
    ),
    Judged(
        "consistent_terms",
        "Does this text use one name for each thing throughout, instead of switching between "
        "synonyms for the same thing?",
        sees_task=False,
    ),
    Judged(
        "literal_language",
        "Does this text say things literally, avoiding metaphors, idioms, hints, and vague terms "
        "such as 'soon' or 'a few'?",
        sees_task=False,
    ),
    Judged(
        "neutral_tone",
        "Is the tone of this text neutral, neither enthusiastic nor aggressive?",
        sees_task=False,
    ),
)

INTRO_CHECK = Judged(
    "intro_states_point",
    "Do these opening sentences state the main point itself, so that a reader who stops here "
    "knows the key result? Score Not met if they only announce what the text will cover.",
    sees_task=False,
    first_sentences=2,
)
RELATIVE_LENGTH = Bound("restraint", "length_ratio", high=1.3)
# Not a shared check: asked of a text with no decision, the judge scored about 0.3, not Fully met.
DECISION_CHECK = Judged(
    "decision_first",
    "This text helps a reader make a decision. Could a reader who stops after the first few lines "
    "say what to do next, or what the choice depends on? Score Not met if background comes first.",
    sees_task=False,
)


BURIED_DECISION = Damage(
    "decision_first",
    "buried-under-background",
    add_opening(
        "Some background first. Several colleagues have looked at this over recent weeks, and "
        "their views covered a range of areas. The history of the topic goes back some time, and "
        "the following paragraphs set out that context in order."
    ),
)

SECURITY_NOTICE = Effect(
    id="security-notice",
    text=(
        "This came from a service I use for my small shop, and I'm not technical.\n\n"
        "Subject: Post-incident communication regarding credential exposure\n\n"
        "On 3 November 2026 at 02:14 UTC our on-call engineer, Tomasz, was paged following anomalous "
        "egress from a build runner on kernel 6.8.0-45. Subsequent forensic analysis attributed this "
        "to a compromised CI dependency, which allowed exfiltration of a subset of API keys issued "
        "before 1 June 2026. Keys issued after that date are not implicated. There is no evidence at "
        "this time that payment card data was accessed, though the investigation remains ongoing and "
        "we expect to publish findings by 28 November 2026. Tenants holding affected credentials are "
        "required to perform rotation via Settings > API Keys prior to 23:59 UTC on 10 November 2026, "
        "after which legacy keys will be administratively revoked, which will cause integrations "
        "reliant upon them to fail."
    ),
    checks=(
        GENERAL_READER,
        INTRO_CHECK,
        RELATIVE_LENGTH,
        ReaderAnswers(
            "reader_success",
            "Using only this text, what must a customer with an older API key do?",
            {
                "replace": "Replace the key in Settings > API Keys",
                "wait": "Wait for the company to replace it",
                "card": "Replace their payment card",
                "unclear": "The text does not say",
            },
            "replace",
        ),
        ReaderAnswers(
            "reader_success",
            "Using only this text, has it been established that payment card data is safe?",
            {
                "safe": "Yes, it is confirmed safe",
                "stolen": "No, card data was stolen",
                "open": "No evidence of access so far, but the investigation is still open",
                "unclear": "The text does not say",
            },
            "open",
        ),
        ReaderAnswers(
            "limits_kept",
            "Using only this text, are API keys issued after 1 June 2026 affected?",
            {"no": "No", "yes": "Yes", "unclear": "The text does not say"},
            "no",
        ),
        Matches("fidelity", r"10 November|November 10|10/11"),
        Matches("fidelity", r"1 June|June 1"),
    ),
    damages=(
        Damage("no_invented_claims", "case-specific-false-claim", add_text("An outside audit has confirmed that all card data is safe.")),
    ),
)

NO_WINNER_DECISION = Effect(
    id="no-winner-decision",
    text=(
        "I have to pick a CRM on Thursday. My needs are: under €500 per month, data hosted in the "
        "EU, and import from Salesforce. These are the notes I was given.\n\n"
        "A number of vendors were assessed following an extended period of market scanning, "
        "including a trade show in Lyon. Alpha costs €450 per month with EU hosting, however no "
        "Salesforce import is offered. Bravo costs €620 per month with EU hosting and a Salesforce "
        "import. Charlie costs €480 per month and has a Salesforce import, but hosting is US only. "
        "Charlie's logo was recently redesigned."
    ),
    checks=(
        GENERAL_READER,
        INTRO_CHECK,
        RELATIVE_LENGTH,
        DECISION_CHECK,
        ReaderAnswers(
            "reader_success",
            "Using only this text, does any option meet all three needs?",
            {
                "alpha": "Yes, Alpha does",
                "bravo": "Yes, Bravo does",
                "charlie": "Yes, Charlie does",
                "none": "No, none meets all three",
                "unclear": "The text does not say",
            },
            "none",
        ),
        ReaderAnswers(
            "reader_success",
            "Using only this text, which need does Bravo fail?",
            {
                "price": "Price",
                "hosting": "EU hosting",
                "import": "Salesforce import",
                "none": "None",
                "unclear": "The text does not say",
            },
            "price",
        ),
        Matches("fidelity", r"€\s?450"),
        Matches("fidelity", r"€\s?620"),
        Matches("fidelity", r"€\s?480"),
    ),
    damages=(
        Damage("no_invented_claims", "case-specific-false-claim", add_text("Alpha also offers a full Salesforce import at no extra cost.")),
        BURIED_DECISION,
    ),
)

FOLLOWUP_PROMPT = "Rewrite your previous message."


def limits_kept(question: str, options: dict[str, str], correct: str) -> ReaderAnswers:
    return ReaderAnswers("limits_kept", question, options, correct)


# Holdout replies have none, because writing their questions would mean reading them.
LIMIT_QUESTIONS = {
    "dev-blood-test": limits_kept(
        "Using only this text, does normal serum iron alone rule out iron overload?",
        {
            "no": "No, transferrin saturation is the more useful number",
            "yes": "Yes, it rules it out",
            "unclear": "The text does not say",
        },
        "no",
    ),
    "dev-home-sale-tax": limits_kept(
        "Using only this text, does the primary residence exemption normally cover a flat that "
        "was rented out?",
        {
            "no": "No, or only partly if the owner lived there for part of the time",
            "yes": "Yes, in full",
            "unclear": "The text does not say",
        },
        "no",
    ),
    "dev-lease-break": limits_kept(
        "Using only this text, does an employer's relocation give an automatic right to break a lease?",
        {
            "no": "No, usually not, and it depends on the place and the lease",
            "yes": "Yes, everywhere",
            "unclear": "The text does not say",
        },
        "no",
    ),
    "dev-rome-fall": limits_kept(
        "Using only this text, how settled is the argument that climate and disease caused the fall?",
        {
            "debated": "It is influential but debated",
            "settled": "It is settled",
            "rejected": "Nearly everyone rejects it",
            "unclear": "The text does not say",
        },
        "debated",
    ),
    "dev-solar-decision": limits_kept(
        "Using only this text, when could buying a battery first make sense?",
        {
            "conditions": "With steep time-of-use tariffs, or a need for backup power",
            "always": "Always",
            "never": "Never",
            "unclear": "The text does not say",
        },
        "conditions",
    ),
    "dev-sourdough": limits_kept(
        "Using only this text, is underproofing the certain cause of this loaf's problem?",
        {
            "likely": "No, it is the most likely of several causes",
            "certain": "Yes, it is certain",
            "unclear": "The text does not say",
        },
        "likely",
    ),
}


# Holdout replies are left out for the same reason.
DECISION_REPLIES = {"dev-solar-decision"}


def frozen_reply(path: Path) -> Effect:
    # The first line of each file is a comment holding the prompt that produced the reply.
    reply = path.read_text(encoding="utf-8").split("\n", 1)[1]
    return Effect(
        id=path.stem,
        prompt=FOLLOWUP_PROMPT,
        previous_reply=reply,
        checks=(
            expertise_check("someone asking about this for the first time, with no background in it."),
            INTRO_CHECK,
            RELATIVE_LENGTH,
            *((LIMIT_QUESTIONS[path.stem],) if path.stem in LIMIT_QUESTIONS else ()),
            *((DECISION_CHECK,) if path.stem in DECISION_REPLIES else ()),
        ),
        damages=(BURIED_DECISION,) if path.stem in DECISION_REPLIES else (),
        holdout=path.stem.startswith("holdout-"),
    )


FROZEN_REPLIES = tuple(
    frozen_reply(path) for path in sorted((Path(__file__).parents[1] / "replies").glob("*.md"))
)

# Each dimension the judge scores has a negative test. Regex and word-limit checks don't need one.
SHARED_DAMAGES = (
    Damage(
        "limits_kept",
        "says-nothing",
        replace_output("There are a number of considerations here. Please consult the original."),
    ),
    Damage("structure", "one-block-of-text", flatten_text),
    Damage("reasoning", "sentences-out-of-order", reverse_sentences),
    Damage(
        "consistent_terms",
        "many-names-for-one-thing",
        add_text(
            "The matter, also called the issue, the situation, the affair, or the topic, stays as "
            "described. That business, this question, and the subject are all unchanged."
        ),
    ),
    Damage(
        "stated_limits",
        "overstated-certainty",
        add_text("All of this is proven beyond doubt, and every expert agrees without exception."),
    ),
    Damage(
        "literal_language",
        "idioms-and-vague-terms",
        add_text(
            "We're in the home stretch, the ball is in your court, and things should land soon-ish, "
            "give or take a few bits and pieces. Food for thought, as they say."
        ),
    ),
    Damage(
        "neutral_tone",
        "shouting-enthusiasm",
        add_text("This is AMAZING news!!! You will absolutely LOVE it, and anyone who disagrees is a fool!"),
    ),
    Damage(
        "intro_states_point",
        "announces-instead-of-stating",
        add_opening("This message explains what happened. It then covers what comes next."),
    ),
    Damage(
        "no_expertise_pollution",
        "unexplained-internals",
        add_text(
            "Separately, the Q3 override in rs_core depends on the KTX shim, as flagged in run 7, "
            "so the PX flag stays on until the gamma cut."
        ),
    ),
    Damage(
        "no_invented_claims",
        "invented-fine",
        add_text("Regulators have since fined the organisation 2 million euros over this matter."),
    ),
    Damage(
        "reader_success",
        "says-nothing",
        replace_output("There are a number of considerations here. Please consult the original."),
    ),
)

EVAL = SkillEval(
    skill="write-better",
    shared_checks=SHARED_CHECKS,
    # These still fail too many negative tests to fail a run, so they are only reported.
    report_only=(
        "consistent_terms",
        "literal_language",
        "no_expertise_pollution",
        "no_invented_claims",
        "reasoning",
        "structure",
    ),
    shared_damages=SHARED_DAMAGES,
    effects=(
        SECURITY_NOTICE,
        NO_WINNER_DECISION,
        *FROZEN_REPLIES,
    ),
)
