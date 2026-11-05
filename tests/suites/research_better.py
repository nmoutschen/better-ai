"""Data for /research-better. Better research means, in separate dimensions:

From the trajectory, meaning every search, result, and message in order:
- neutral_start: the first searches do not assume the answer the agent already expects.
- discovery: later searches use terms that earlier results revealed. This is measured, because
  the judge did not notice when every search was replaced by the first.
- follow_through: questions raised along the way are pursued before the agent stops. No later
  searches score 0, because the judge gave about 0.5 to runs that never searched.
- source_scrutiny: the agent reads and weighs sources instead of trusting snippets.
- disambiguation: an ambiguous topic is raised before any meaning is assumed.

From the final output:
- breadth: the findings draw on many independent sources.
- evidence_handling: disagreement and weak evidence are reported.
- reader_success: a reader of the findings alone gets the right conclusion.

Users invoke this skill by name, as /research-better TOPIC, so there are no trigger tests.

Each prior-heavy topic has a well-known answer that a model is likely to already hold.
"""

from harness import (
    Bound,
    Damage,
    Effect,
    Judged,
    OnTrajectory,
    ReaderAnswers,
    SkillEval,
    lead_first_search,
    repeat_first_search,
    replace_output,
    skip_reading_sources,
    stop_after_first_search,
)


WEB = ("WebSearch", "WebFetch")


def research_checks() -> tuple:
    return (
        Bound("discovery", "terms_from_results", low=10),
        Bound("follow_through", "later_searches", low=1),
        OnTrajectory(
            "follow_through",
            "After its first searches, did the agent run further searches on questions, "
            "disagreements, or gaps that the results raised? Score Not met if it stopped after its "
            "first searches.",
            searches_only=True,
        ),
        OnTrajectory(
            "source_scrutiny",
            "Did the agent open full source pages, instead of reading only search results? Score "
            "Not met if it never opened a page.",
            searches_only=True,
        ),
        Bound("breadth", "domains", low=5),
        Judged(
            "evidence_handling",
            "Does the output say where sources disagree or where the evidence is weak?",
        ),
        Judged("evidence_handling", "Does the output name the source of each main claim?"),
    )


EASTER_ISLAND = Effect(
    id="easter-island-prior",
    text="what happened to the society of Easter Island (Rapa Nui)?",
    prompt="Research this topic: what happened to the society of Easter Island (Rapa Nui)?",
    tools=WEB,
    checks=(
        *research_checks(),
        Judged(
            "neutral_start",
            "These are an agent's first web searches on the task, made before it saw any results. "
            "Is every one of them neutral about the answer? Score Not met if even one assumes an "
            "answer. On this topic that means assuming ecocide, deforestation, a collapse, or the "
            "account of a particular author.",
            sees_task=False,
            first_searches=True,
        ),
        ReaderAnswers(
            "reader_success",
            "Using only this text, is the idea that islanders destroyed their own society settled?",
            {
                "settled": "Yes, it is settled",
                "contested": "No, it is contested",
                "unclear": "The text does not say",
            },
            "contested",
        ),
    ),
    damages=(
        Damage(
            "neutral_start",
            "leading-search",
            lead_first_search("Jared Diamond ecocide deforestation caused Easter Island collapse"),
        ),
    ),
)

EXPERTISE_PRIOR = Effect(
    id="expertise-prior",
    text="how much does deliberate practice explain differences in skill?",
    prompt="Research this topic: how much does deliberate practice explain differences in skill?",
    tools=WEB,
    checks=(
        *research_checks(),
        Judged(
            "neutral_start",
            "These are an agent's first web searches on the task, made before it saw any results. "
            "Is every one of them neutral about the answer? Score Not met if even one assumes an "
            "answer. On this topic that means assuming the 10,000-hour rule or naming a particular "
            "researcher's position.",
            sees_task=False,
            first_searches=True,
        ),
        ReaderAnswers(
            "reader_success",
            "Using only this text, do researchers agree on how much practice explains?",
            {"yes": "Yes", "no": "No, estimates and interpretations differ",
             "unclear": "The text does not say"},
            "no",
        ),
    ),
    damages=(
        Damage(
            "neutral_start",
            "leading-search",
            lead_first_search("10,000 hour rule deliberate practice proves expertise Gladwell"),
        ),
    ),
    holdout=True,
)

UNDER_COVERED_TOPIC = Effect(
    id="under-covered-topic",
    text="how do mid-sized Nigerian cities organise informal waste collection?",
    prompt="Research this topic: how do mid-sized Nigerian cities organise informal waste collection?",
    tools=WEB,
    checks=(
        *research_checks(),
        OnTrajectory(
            "follow_through",
            "Did the later searches look for Nigerian cities other than Lagos and Abuja? Score Not "
            "met if there were no later searches.",
            searches_only=True,
        ),
        Judged("evidence_handling", "Does the output say what the search could not find?"),
    ),
)

AMBIGUOUS_TOPIC = Effect(
    id="ambiguous-topic",
    text="transformers.",
    prompt="Research this topic: transformers.",
    tools=WEB,
    checks=(
        OnTrajectory(
            "disambiguation",
            "Did the agent name more than one possible meaning of the topic, and ask which one "
            "is meant, instead of researching only one?",
        ),
    ),
)

SIMPLE_FACT = Effect(
    id="simple-fact",
    text="At sea level, what temperature does water boil at, in Celsius?",
    prompt="At sea level, what temperature does water boil at, in Celsius?",
    tools=WEB,
    checks=(
        # Negative case: the skill should not turn a simple question into a research project.
        Bound("restraint", "searches", high=2),
        Bound("restraint", "words", high=120),
        ReaderAnswers(
            "reader_success",
            "Using only this text, at what temperature does water boil at sea level?",
            {"100": "100 °C", "other": "Another temperature", "unclear": "The text does not say"},
            "100",
        ),
    ),
)

# Each scored dimension has a negative test, built by damaging a real run.
SHARED_DAMAGES = (
    Damage("discovery", "repeats-first-search", repeat_first_search),
    Damage("follow_through", "stops-early", stop_after_first_search),
    Damage("source_scrutiny", "snippets-only", skip_reading_sources),
    Damage(
        "evidence_handling",
        "no-caveats-or-sources",
        replace_output("The answer is clear and everyone agrees on it."),
    ),
    Damage(
        "reader_success",
        "says-nothing",
        replace_output("This topic has many interesting aspects worth exploring further."),
    ),
    Damage(
        "disambiguation",
        "assumes-one-meaning",
        replace_output("Transformers are neural networks. Here is what I found about them."),
    ),
)

EVAL = SkillEval(
    skill="research-better",
    shared_damages=SHARED_DAMAGES,
    effects=(EASTER_ISLAND, EXPERTISE_PRIOR, UNDER_COVERED_TOPIC, AMBIGUOUS_TOPIC, SIMPLE_FACT),
)
