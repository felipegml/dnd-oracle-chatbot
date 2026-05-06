"""
rag.py — indexes all Open5e JSON files into ChromaDB
"""

import json
import os
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer

os.environ["ANONYMIZED_TELEMETRY"] = "False"

DATA_DIR    = Path(__file__).parent / "data"
CHROMA_PATH = Path(__file__).parent / "chroma_db"

_client     = None
_collection = None
_embedder   = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        print("[RAG] Loading embedding model...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _load(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"[RAG] WARNING: {filename} not found — skipping.")
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    _collection = _client.get_or_create_collection(
        name="dnd5e",
        metadata={"hnsw:space": "cosine"},
    )

    if _collection.count() == 0:
        print("[RAG] Building index from data/ files...")
        _index_all()

    print(f"[RAG] Ready — {_collection.count()} chunks indexed.")
    return _collection


# ── CHUNKERS ──────────────────────────────────────────────────

def _chunk_spells(records: list) -> list[tuple[str, str]]:
    chunks = []
    for s in records:
        slug = s.get("slug", s.get("name", "unknown")).replace(" ", "_").lower()
        classes = s.get("dnd_class", "") or s.get("class", "")
        text = (
            f"Spell: {s.get('name','')}. "
            f"Level {s.get('level_int', s.get('level', '?'))} {s.get('school','')}. "
            f"Casting time: {s.get('casting_time','')}. "
            f"Range: {s.get('range','')}. "
            f"Duration: {s.get('duration','')}. "
            f"Components: {s.get('components','')}. "
            f"Classes: {classes}. "
            f"{s.get('desc','')}"
        )
        chunks.append((f"spell_{slug}", text[:1200]))
    return chunks


def _chunk_classes(records: list) -> list[tuple[str, str]]:
    chunks = []
    for c in records:
        slug = c.get("slug", c.get("name", "unknown")).lower()
        name = c.get("name", "")

        # Overview
        chunks.append((f"class_{slug}_overview", (
            f"Class: {name}. "
            f"Hit die: {c.get('hit_dice','')}. "
            f"HP at 1st level: {c.get('hp_at_1st_level','')}. "
            f"HP at higher levels: {c.get('hp_at_higher_levels','')}. "
            f"Saving throws: {c.get('saving_throws','')}. "
            f"{c.get('desc','')}"
        )[:1200]))

        # Proficiencies
        chunks.append((f"class_{slug}_proficiencies", (
            f"{name} proficiencies. "
            f"Armor: {c.get('prof_armor','')}. "
            f"Weapons: {c.get('prof_weapons','')}. "
            f"Tools: {c.get('prof_tools','')}. "
            f"Skills: {c.get('prof_skills','')}."
        )[:1200]))

        # Equipment
        if c.get("equipment"):
            chunks.append((f"class_{slug}_equipment",
                f"{name} starting equipment: {c.get('equipment','')}."[:1200]))

        # Subclasses (archetypes)
        archetypes = c.get("archetypes", [])
        if archetypes:
            names = ", ".join(a.get("name","") for a in archetypes)
            descs = " | ".join(
                f"{a.get('name','')}: {a.get('desc','')[:200]}"
                for a in archetypes
            )
            chunks.append((f"class_{slug}_subclasses",
                f"{name} subclasses: {names}. {descs}"[:1200]))

        # Class table / features
        if c.get("table"):
            chunks.append((f"class_{slug}_table",
                f"{name} progression table: {c.get('table','')}"[:1200]))

    return chunks


def _chunk_monsters(records: list) -> list[tuple[str, str]]:
    chunks = []
    for m in records:
        slug = m.get("slug", m.get("name","unknown")).replace(" ","_").lower()
        text = (
            f"Monster: {m.get('name','')}. "
            f"CR {m.get('challenge_rating','')}. "
            f"Type: {m.get('type','')}. "
            f"Size: {m.get('size','')}. "
            f"AC: {m.get('armor_class','')}. "
            f"HP: {m.get('hit_points','')} ({m.get('hit_dice','')})."
            f"Speed: {m.get('speed','')}. "
            f"STR {m.get('strength','')} DEX {m.get('dexterity','')} "
            f"CON {m.get('constitution','')} INT {m.get('intelligence','')} "
            f"WIS {m.get('wisdom','')} CHA {m.get('charisma','')}. "
            f"{m.get('desc','')[:400]}"
        )
        chunks.append((f"monster_{slug}", text[:1200]))
    return chunks


def _chunk_races(records: list) -> list[tuple[str, str]]:
    chunks = []
    for r in records:
        slug = r.get("slug", r.get("name","unknown")).lower()
        text = (
            f"Race: {r.get('name','')}. "
            f"Size: {r.get('size','')}. "
            f"Speed: {r.get('speed','')}. "
            f"Age: {r.get('age','')}. "
            f"Alignment: {r.get('alignment','')}. "
            f"Ability bonuses: {r.get('ability_score_increase','')}. "
            f"Languages: {r.get('languages','')}. "
            f"{r.get('desc','')[:500]}"
        )
        chunks.append((f"race_{slug}", text[:1200]))

        # Subraces
        for sub in r.get("subraces", []):
            sslug = sub.get("slug", sub.get("name","")).lower()
            chunks.append((f"race_{slug}_sub_{sslug}", (
                f"Subrace: {sub.get('name','')} ({r.get('name','')}). "
                f"{sub.get('desc','')[:600]}"
            )[:1200]))
    return chunks


def _chunk_backgrounds(records: list) -> list[tuple[str, str]]:
    chunks = []
    for b in records:
        slug = b.get("slug", b.get("name","unknown")).lower()
        text = (
            f"Background: {b.get('name','')}. "
            f"Skill proficiencies: {b.get('skill_proficiencies','')}. "
            f"Tool proficiencies: {b.get('tool_proficiencies','')}. "
            f"Languages: {b.get('languages','')}. "
            f"Equipment: {b.get('equipment','')}. "
            f"{b.get('desc','')[:500]}"
        )
        chunks.append((f"background_{slug}", text[:1200]))
    return chunks


def _chunk_feats(records: list) -> list[tuple[str, str]]:
    chunks = []
    for f in records:
        slug = f.get("slug", f.get("name","unknown")).lower()
        text = (
            f"Feat: {f.get('name','')}. "
            f"Prerequisite: {f.get('prerequisite','None')}. "
            f"{f.get('desc','')}"
        )
        chunks.append((f"feat_{slug}", text[:1200]))
    return chunks


def _chunk_conditions(records: list) -> list[tuple[str, str]]:
    chunks = []
    for c in records:
        slug = c.get("slug", c.get("name","unknown")).lower()
        text = f"Condition: {c.get('name','')}. {c.get('desc','')}"
        chunks.append((f"condition_{slug}", text[:1200]))
    return chunks


def _chunk_magicitems(records: list) -> list[tuple[str, str]]:
    chunks = []
    for m in records:
        slug = m.get("slug", m.get("name","unknown")).replace(" ","_").lower()
        text = (
            f"Magic item: {m.get('name','')}. "
            f"Type: {m.get('type','')}. "
            f"Rarity: {m.get('rarity','')}. "
            f"Requires attunement: {m.get('requires_attunement','no')}. "
            f"{m.get('desc','')[:600]}"
        )
        chunks.append((f"magicitem_{slug}", text[:1200]))
    return chunks


def _chunk_weapons(records: list) -> list[tuple[str, str]]:
    chunks = []
    for w in records:
        slug = w.get("slug", w.get("name","unknown")).replace(" ","_").lower()
        text = (
            f"Weapon: {w.get('name','')}. "
            f"Category: {w.get('category','')}. "
            f"Damage: {w.get('damage_dice','')} {w.get('damage_type','')}. "
            f"Weight: {w.get('weight','')}. "
            f"Cost: {w.get('cost','')}. "
            f"Properties: {w.get('properties','')}."
        )
        chunks.append((f"weapon_{slug}", text[:1200]))
    return chunks


def _chunk_armor(records: list) -> list[tuple[str, str]]:
    chunks = []
    for a in records:
        slug = a.get("slug", a.get("name","unknown")).replace(" ","_").lower()
        text = (
            f"Armor: {a.get('name','')}. "
            f"Category: {a.get('category','')}. "
            f"AC: {a.get('base_ac','')}. "
            f"Strength requirement: {a.get('strength_requirement','')}. "
            f"Stealth: {a.get('stealth_disadvantage','no disadvantage')}. "
            f"Weight: {a.get('weight','')}. "
            f"Cost: {a.get('cost','')}."
        )
        chunks.append((f"armor_{slug}", text[:1200]))
    return chunks


def _chunk_planes(records: list) -> list[tuple[str, str]]:
    chunks = []
    for p in records:
        slug = p.get("slug", p.get("name","unknown")).lower()
        text = f"Plane: {p.get('name','')}. {p.get('desc','')[:800]}"
        chunks.append((f"plane_{slug}", text[:1200]))
    return chunks


def _chunk_sections(records: list) -> list[tuple[str, str]]:
    chunks = []
    for s in records:
        slug = s.get("slug", s.get("name","unknown")).lower()
        text = (
            f"Rule/Section: {s.get('name','')}. "
            f"Parent: {s.get('parent','')}. "
            f"{s.get('desc','')[:800]}"
        )
        chunks.append((f"section_{slug}", text[:1200]))
    return chunks


# ── MAIN INDEXER ───────────────────────────────────────────────

CHUNKERS = {
    "spells.json":      _chunk_spells,
    "classes.json":     _chunk_classes,
    "monsters.json":    _chunk_monsters,
    "races.json":       _chunk_races,
    "backgrounds.json": _chunk_backgrounds,
    "feats.json":       _chunk_feats,
    "conditions.json":  _chunk_conditions,
    "magicitems.json":  _chunk_magicitems,
    "weapons.json":     _chunk_weapons,
    "armor.json":       _chunk_armor,
    "planes.json":      _chunk_planes,
    "sections.json":    _chunk_sections,
}


def _index_all():
    embedder   = _get_embedder()
    all_ids    = []
    all_texts  = []

    for filename, chunker in CHUNKERS.items():
        records = _load(filename)
        if not records:
            continue
        chunks = chunker(records)

        # Deduplicate IDs
        seen = set(all_ids)
        for cid, ctext in chunks:
            if cid not in seen:
                all_ids.append(cid)
                all_texts.append(ctext)
                seen.add(cid)

        print(f"[RAG] {filename}: {len(chunks)} chunks")

    # Also index dialogs.json if present
    dialogs_data = _load("dialogs.json")
    if dialogs_data:
        dialogs = dialogs_data if isinstance(dialogs_data, list) else dialogs_data.get("dialogs", [])
        for i, dialog in enumerate(dialogs):
            for j, resp in enumerate(dialog.get("responses", [])):
                cid = f"dialog_{i}_{j}"
                if cid not in set(all_ids):
                    all_ids.append(cid)
                    all_texts.append(resp)

    print(f"[RAG] Embedding {len(all_ids)} chunks (this may take a few minutes)...")

    # Batch embed to avoid memory issues with large datasets
    BATCH = 128
    all_embeddings = []
    for i in range(0, len(all_texts), BATCH):
        batch = all_texts[i:i+BATCH]
        vecs  = embedder.encode(batch, show_progress_bar=False).tolist()
        all_embeddings.extend(vecs)
        print(f"[RAG] Embedded {min(i+BATCH, len(all_texts))}/{len(all_ids)}")

    # Store in batches
    for i in range(0, len(all_ids), BATCH):
        _collection.add(
            ids=all_ids[i:i+BATCH],
            documents=all_texts[i:i+BATCH],
            embeddings=all_embeddings[i:i+BATCH],
        )

    print(f"[RAG] Done — {len(all_ids)} chunks stored.")


def retrieve(query: str, n_results: int = 5) -> list[str]:
    col      = _get_collection()
    embedder = _get_embedder()
    vec      = embedder.encode([query], show_progress_bar=False).tolist()
    results  = col.query(query_embeddings=vec, n_results=min(n_results, col.count()))
    return results["documents"][0] if results["documents"] else []