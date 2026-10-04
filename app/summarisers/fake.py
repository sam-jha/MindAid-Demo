"""FakeSummariser: no AI, nothing leaves this computer.

- For the seeded DEMO patients it returns fixed, fictional summaries (so the demo shows
  different priorities). The quoted excerpts match the seeded entries in scripts/seed.py.
- For anyone else it returns a clearly labelled placeholder and does NO analysis.
  It never pretends to analyse real text.
"""
from app.models import Entry

# Keyed by the patient's first name. Only used when ALL the entries are seeded demo entries.
DEMO_SUMMARIES = {
    "Maya": {
        "narrative": (
            "Maya describes a stressful start to the semester with a heavy workload and growing "
            "worry about falling behind. Over the two weeks her sleep has worsened, she has been "
            "avoiding friends and family, and her mood has become flatter and more irritable. "
            "The breathing exercise from the last session gave only short-lived relief."
        ),
        "themes": ["Academic pressure", "Poor sleep", "Social withdrawal", "Irritability", "Limited relief from coping skill"],
        "mood_pattern": "Anxious early on, drifting to flat and tired over the fortnight.",
        "concerning_content": [
            {"excerpt": "I keep cancelling on my friends because I just can't face people right now.",
             "note": "Social withdrawal that appears to be increasing."},
            {"excerpt": "I've barely slept more than four hours most nights this week.",
             "note": "Sustained sleep loss, linked by Maya to irritability."},
        ],
        "priority": {"level": "notable",
                     "reason": "Worsening sleep and withdrawal over two weeks. No statements about self-harm "
                               "were flagged in these entries, but that is not an assurance about risk."},
        "suggested_session_focus": "Sleep, avoidance of friends and family, and whether the breathing exercise needs adapting.",
        "uncertainty_note": "Based on six short entries. How Maya is doing outside what she wrote is unknown.",
    },
    "James": {
        "narrative": (
            "James writes about job searching and repeated rejections after losing work. Over the "
            "fortnight his drinking appears to be increasing, he is avoiding his brother, and he is "
            "spending days in bed. The two most recent entries contain statements of hopelessness "
            "and a statement about others being better off without him."
        ),
        "themes": ["Unemployment and rejection", "Increasing alcohol use", "Isolation", "Hopelessness"],
        "mood_pattern": "Low and declining, with growing hopelessness in the most recent entries.",
        "concerning_content": [
            {"excerpt": "Sometimes I think everyone would be better off without me.",
             "note": "May indicate passive suicidal thoughts. Written in the most recent entry."},
            {"excerpt": "I don't see the point in any of this anymore.",
             "note": "Expression of hopelessness."},
            {"excerpt": "Drinking most evenings now.",
             "note": "Alcohol described as the only thing that quiets his head."},
        ],
        "priority": {"level": "urgent",
                     "reason": "Statements that may indicate passive suicidal thoughts in the latest entries. "
                               "Clinician review is recommended soon."},
        "suggested_session_focus": "Direct risk assessment, alcohol use, isolation from family, and practical support around work.",
        "uncertainty_note": "Entries are brief and cannot show intent or plans. Read the raw entries; do not rely on this summary alone.",
    },
    "Priya": {
        "narrative": (
            "Priya describes nervousness before a work presentation, which she managed with practice, "
            "breathing exercises and walks. The presentation went well and she received positive "
            "feedback. She spent time with her sister and mentions only mild tiredness at the end."
        ),
        "themes": ["Performance anxiety", "Effective coping skills", "Social connection", "Mild tiredness"],
        "mood_pattern": "Nervous, then relieved and positive, and steady since.",
        "concerning_content": [],
        "priority": {"level": "routine",
                     "reason": "Entries describe manageable stress and use of coping strategies. Nothing was flagged, "
                               "which is not an assurance of safety."},
        "suggested_session_focus": "Reinforce the coping strategies that worked and check how Priya is sleeping.",
        "uncertainty_note": "Based on six short entries. Absence of flagged content does not mean nothing is wrong.",
    },
}


class FakeSummariser:
    def summarise(self, entries: list[Entry]) -> dict:
        if entries and all(e.is_demo for e in entries):
            first_name = entries[0].patient.name.split()[0]
            fixed = DEMO_SUMMARIES.get(first_name)
            if fixed:
                return {**fixed, "generated_by": "fake"}
        return {
            "narrative": "FAKE SUMMARISER - placeholder output, no analysis performed.",
            "themes": [],
            "mood_pattern": "Not assessed.",
            "concerning_content": [],
            "priority": {"level": "unassessed", "reason": "No analysis was performed."},
            "suggested_session_focus": "Not assessed. Read the raw entries.",
            "uncertainty_note": "This is not a summary. The fake summariser does not read or analyse entry text.",
            "generated_by": "fake",
        }
