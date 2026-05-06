import json
import random
import re
from pathlib import Path
from typing import Optional

DIALOGS_PATH = Path(__file__).parent / "dialogs.json"

CLASS_NAMES = [
    "barbarian", "bard", "cleric", "druid", "fighter",
    "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"
]

INTENT_PATTERNS = {
    "hit_die":      [r"\bhit die\b", r"\bhit dice\b", r"\bd\d+\b", r"\bhp\b", r"\bhit points?\b", r"\bhealth\b"],
    "spellcasting": [r"\bspell", r"\bcaster\b", r"\bcasting\b", r"\bmagic\b", r"\bspellcasting\b"],
    "subclasses":   [r"\bsubclass", r"\bpath\b", r"\barchetype\b", r"\bcollege\b", r"\bdomain\b", r"\boath\b", r"\bschool\b", r"\btradition\b", r"\bcircle\b"],
    "features":     [r"\bfeature", r"\babilit", r"\bpower", r"\bskill", r"\bwhat can", r"\bwhat do", r"\btell me about\b"],
    "armor":        [r"\barmor\b", r"\barmour\b", r"\bshield", r"\bac\b", r"\bdefense\b"],
    "weapons":      [r"\bweapon", r"\bproficien", r"\bsword\b", r"\bbow\b", r"\bdagger\b"],
    "saving_throw": [r"\bsaving throw", r"\bsave\b", r"\bsaves\b"],
    "primary":      [r"\bprimary ability\b", r"\bmain stat\b", r"\bkey ability\b", r"\bprimary stat\b"],
    "overview":     [r"\btell me about\b", r"\bwhat is\b", r"\bexplain\b", r"\bdescribe\b", r"\boverview\b", r"\binfo\b", r"\babout\b"],
}


def load_dialogs() -> dict:
    with open(DIALOGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_class(text: str) -> Optional[str]:
    for cls in CLASS_NAMES:
        if re.search(rf"\b{cls}\b", text):
            return cls
    return None


def detect_intent(text: str) -> Optional[str]:
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                return intent
    return None


def build_class_response(cls_data: dict, intent: Optional[str]) -> str:
    name = cls_data["name"]

    if intent == "hit_die":
        return f"The {name} uses a **{cls_data['hit_die']}** as its hit die."

    if intent == "spellcasting":
        if cls_data["spellcasting"]:
            ability = cls_data.get("spellcasting_ability", "unknown")
            slots = cls_data.get("spell_slots", "")
            return (f"Yes, the {name} is a spellcaster! "
                    f"Spellcasting ability: **{ability}**. "
                    f"Spell slots: {slots}.")
        else:
            return f"No, the {name} does not cast spells. It is a purely martial class."

    if intent == "subclasses":
        subs = ", ".join(cls_data["subclasses"])
        return f"The {name} subclasses (chosen at level 3, unless noted) are: **{subs}**."

    if intent == "armor":
        armor = ", ".join(cls_data["armor_proficiencies"])
        return f"The {name} is proficient with: **{armor}**."

    if intent == "weapons":
        weapons = ", ".join(cls_data["weapon_proficiencies"])
        return f"The {name} is proficient with: **{weapons}**."

    if intent == "saving_throw":
        saves = " and ".join(cls_data["saving_throws"])
        return f"The {name} has proficiency in **{saves}** saving throws."

    if intent == "primary":
        return f"The {name}'s primary ability is **{cls_data['primary_ability']}**."

    if intent == "features":
        lines = []
        for lvl, feats in sorted(cls_data["features"].items(), key=lambda x: int(x[0])):
            lines.append(f"Lvl {lvl}: {', '.join(feats)}")
        return f"**{name} features:**\n" + "\n".join(lines)

    # Default: full overview
    desc = cls_data["description"]
    hd = cls_data["hit_die"]
    primary = cls_data["primary_ability"]
    saves = " & ".join(cls_data["saving_throws"])
    subs = ", ".join(cls_data["subclasses"])
    spell_info = ""
    if cls_data["spellcasting"]:
        spell_info = f" Spellcasting: {cls_data['spellcasting_ability']} ({cls_data.get('spell_slots', '')})."
    else:
        spell_info = " No spellcasting."

    return (
        f"**{name}** — {desc}\n"
        f"Hit Die: {hd} | Primary: {primary} | Saves: {saves}."
        f"{spell_info}\n"
        f"Subclasses: {subs}."
    )


def get_response(user_message: str) -> str:
    dialogs = load_dialogs()
    normalized = user_message.lower().strip()

    # 1. Check if a class is mentioned
    cls_key = detect_class(normalized)
    if cls_key:
        cls_data = dialogs["classes"][cls_key]
        intent = detect_intent(normalized)
        return build_class_response(cls_data, intent)

    # 2. Check general dialog patterns
    for dialog in dialogs["dialogs"]:
        for pattern in dialog["patterns"]:
            if re.search(rf"\b{re.escape(pattern)}\b", normalized):
                return random.choice(dialog["responses"])

    # 3. Fallback
    return random.choice(dialogs["fallback_responses"])