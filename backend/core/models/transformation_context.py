"""
TransformationContext — UNIVERSAL_TRANSFORMATION_CONTRACT (§1)
===============================================================
Assembles the LLM prompt STRICTLY from the caller's PreservationProfile and
the SourceDNACluster. Sections are conditionally injected: a toggle that is
OFF must produce NO source-derived text for that DNA category, which is what
makes the strict narrative separation auditable at the string level.

D3/Q1 verdict encoded here: CharacterMode.MIXED degrades to
PRESERVE_SOURCE ∩ intent.requested_character_ids — the compiled prompt keeps
ONLY the explicitly requested characters and instructs the model to invent
replacements for everything else.
"""
import json
from typing import List

from core.models.clone_intent import (
    CharacterMode,
    CloneIntent,
    EnvironmentMode,
    StoryMode,
)
from core.models.dna import SourceDNACluster


def effective_character_mode(intent: CloneIntent) -> CharacterMode:
    """D3 degradation: MIXED == PRESERVE_SOURCE restricted to requested IDs."""
    if intent.character_mode == CharacterMode.MIXED:
        return (
            CharacterMode.PRESERVE_SOURCE
            if intent.requested_character_ids
            else CharacterMode.CREATE_NEW
        )
    return intent.character_mode


def _beat_timing_table(source_dna: SourceDNACluster) -> str:
    """Structure-only timing table (schema §3 allows timings, never prose)."""
    ns = source_dna.narrative_structure_dna
    if ns is None or not ns.beat_types:
        return ""
    lines = [
        f"  - {i + 1}. {btype}" for i, btype in enumerate(ns.beat_types)
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Viral-retention engineering constants & helpers (Wow-Moment upgrade)
# ─────────────────────────────────────────────────────────────
_WORDS_PER_SECOND_SPOKEN = 2.8   # punchy short-form VO cadence
_VEO_TECHNIQUES = (
    "slow-motion impact frame",
    "sudden hyper-lapse",
    "dramatic lighting shift",
    "dolly-zoom reveal",
    "macro detail insert",
    "speed-ramp collision",
)


def _vo_word_cap(avg_shot_s: float) -> int:
    """Spoken-word ceiling per scene (~2.8 words/sec), floored at 3."""
    return max(3, int(round(avg_shot_s * _WORDS_PER_SECOND_SPOKEN)))


def _wow_moment_clause(source_dna: SourceDNACluster, *, exact: bool) -> str:
    """
    THE WOW MOMENT — the engineered peak of the script.

    When `exact` is True (structure/trend preservation ON), the twist is pinned
    to the source's MEASURED climax position (NarrativeStructureDNA.
    climax_position_percent). Otherwise a retention-optimal 65-80% window is
    mandated. Either way the twist must shatter the CINEMATIC VISUAL METAPHOR
    using Veo-grade technique language.
    """
    ns = source_dna.narrative_structure_dna
    techniques = ", ".join(_VEO_TECHNIQUES)
    if exact and ns is not None:
        placement = (
            f"at EXACTLY {ns.climax_position_percent:.0f}% of the runtime - "
            "the same beat where the source video peaked"
        )
    else:
        placement = "between 65% and 80% of the runtime"
    return (
        "THE WOW MOMENT (NON-NEGOTIABLE):\n"
        f"- Engineer ONE jaw-dropping Climax/Twist {placement}.\n"
        "- Make it VISUALLY STRIKING and exploit Veo's full cinematic range:\n"
        f"  {techniques}.\n"
        "- Pay it off by BREAKING the CINEMATIC VISUAL METAPHOR: the metaphor "
        "shatters, flips, or reveals its opposite.\n"
        "- Escalate HIGH STAKES monotonically toward this frame; mark the "
        "scene explicitly as the emotional and visual peak."
    )


class TransformationContext:
    """Scoped container providing ONLY authorized DNA context to the LLM."""

    def compile_prompt(self, intent: CloneIntent, source_dna: SourceDNACluster) -> str:
        profile = intent.preservation_profile
        ci = intent.creative_intent
        dna = source_dna or SourceDNACluster()
        sections: List[str] = []

        # ── 1. Primary Creative Directive ────────────────────────────
        sections.append(
            "You are the AI Universal Creative Director.\n"
            "Your mission is to write a BRAND NEW original storyboard driven "
            "by the User's Creative Intent.\n"
            f"Story Topic: {ci.topic}\n"
            f"Story Detail: {ci.story_change or 'Invent an original comedic/dramatic narrative'}\n"
            f"Niche: {ci.niche} | Genre: {ci.genre} | Tone: {ci.tone}\n"
            f"Audience: {ci.audience}\n"
            f"Language: {ci.language}\n"
            f"Target Duration: {ci.target_duration_seconds or 15.0}s\n"
            f"Aspect Ratio: {ci.aspect_ratio}\n"
            "Mission Class: VIRAL RETENTION ENGINEERING - treat every scene "
            "as a retention battle you must win."
        )

        # ── 1.5 VIRAL RETENTION MANDATE — Metaphor Translation ───────
        sections.append(
            "VIRAL RETENTION MANDATE - CINEMATIC VISUAL METAPHOR:\n"
            "This is not a script. It is a retention weapon. Every decision "
            "below serves one metric: WATCH TIME.\n"
            "1. Distill the topic's core tension into ONE dominant CINEMATIC "
            "VISUAL METAPHOR (e.g. debt -> drowning in open ocean; physical "
            "weakness -> trapped beneath an impossible barbell).\n"
            "2. Establish the metaphor VISUALLY in the first shot, then "
            "ESCALATE its scale every scene until the WOW MOMENT shatters it.\n"
            "3. Translate abstract concepts into PHYSICAL CINEMATIC EXTREMES: "
            "crushing scale, violent weather, impossible geometry.\n"
            "4. BANNED: people sitting in rooms talking; stock-footage "
            "energy; literal explanations.\n"
            "5. Open a curiosity loop by scene 2; pay it off only at the WOW "
            "MOMENT."
        )

        # ── 2. Visual Style Preservation ─────────────────────────────
        if profile.preserve_visual_style and dna.visual_style is not None:
            vs = dna.visual_style
            sections.append(
                "SOURCE VISUAL STYLE (MANDATORY TO PRESERVE):\n"
                f"- Art Style: {vs.art_style}\n"
                f"- Render Language: {vs.render_language}\n"
                f"- Lighting & Ambiance: {vs.lighting_style}\n"
                f"- Color Palette: {vs.color_palette}\n"
                f"- Realism Level: {vs.realism_level}"
            )
        else:
            sections.append(
                "VISUAL STYLE POLICY: DO NOT preserve the source art style. "
                "INVENT a fresh, fitting visual style tailored to the new story."
            )

        # ── 3. Character Policy (D3-degraded modes) ──────────────────
        eff_mode = effective_character_mode(intent)
        if eff_mode == CharacterMode.PRESERVE_SOURCE and dna.character_dna is not None:
            cd = dna.character_dna
            sections.append(
                "SOURCE CHARACTERS (PRESERVE EXACT APPEARANCE):\n"
                f"{json.dumps(cd.characters, indent=1)}"
            )
            if intent.character_mode == CharacterMode.MIXED:
                keep = ", ".join(intent.requested_character_ids) or "(all listed above)"
                sections.append(
                    "MIXED CHARACTER MODE (DEGRADED): preserve ONLY these "
                    f"requested characters: {keep}. INVENT new replacements "
                    "for every other role."
                )
        else:
            sections.append(
                "CHARACTER POLICY: DO NOT use source characters. INVENT brand "
                "new characters matching the story, styled in the authoritative "
                "art style. Use clean IDs like 'char_lead_1'."
            )

        # ── 4. Environment Policy ────────────────────────────────────
        if intent.environment_mode == EnvironmentMode.PRESERVE_SOURCE and dna.environment_dna is not None:
            env = dna.environment_dna
            sections.append(
                "ENVIRONMENT (PRESERVE SOURCE WORLD):\n"
                f"- Setting Type: {env.setting_type}\n"
                f"- Mood: {env.environmental_mood}"
            )
        elif intent.environment_mode == EnvironmentMode.ADAPT and dna.environment_dna is not None:
            env = dna.environment_dna
            sections.append(
                "ENVIRONMENT POLICY (ADAPT): keep the source world AESTHETIC "
                f"({env.setting_type} / {env.environmental_mood}) but relocate "
                f"scene locations to serve the new story ({ci.topic})."
            )
        else:
            sections.append(
                "ENVIRONMENT POLICY: Create NEW settings and locations "
                f"appropriate for {ci.topic}."
            )

        # ── 5. Camera Language & Pacing — CADENCE IS KING ────────────
        if profile.preserve_camera_language and dna.camera_dna is not None:
            cam = dna.camera_dna
            sections.append(
                "CAMERA LANGUAGE (PRESERVE): use shot types "
                f"{cam.dominant_shot_types} and motions {cam.motion_styles}. "
                "Match the source lens energy EXACTLY - the camera IS the "
                "adrenaline."
            )

        ns_dna = dna.narrative_structure_dna
        if profile.preserve_pacing_editing and dna.pacing_dna is not None:
            pacing = dna.pacing_dna
            vo_cap = _vo_word_cap(pacing.average_shot_duration)
            total_target = ci.target_duration_seconds or 15.0
            hook_len = (
                round(ns_dna.hook_duration_seconds, 1)
                if ns_dna is not None else 2.0
            )
            sections.append(
                "PACING (PRESERVE RHYTHM) - CADENCE IS KING:\n"
                f"- Average shot duration ~{pacing.average_shot_duration:.1f}s, "
                f"{pacing.cut_frequency} cutting rhythm, "
                f"{pacing.overall_intensity} intensity.\n"
                "- THE 3-SECOND RULE: the opening hook must land its full "
                f"punch within the first {max(1.0, hook_len):.1f}s - MIRROR "
                "the source hook's LENGTH and CHAOS LEVEL precisely, but aim "
                "it at the new topic with HIGH STAKES energy.\n"
                f"- SPOKEN WORD BUDGET: voice-over per scene MUST NOT exceed "
                f"{vo_cap} words ({pacing.average_shot_duration:.1f}s x 2.8 "
                "words/sec). Total spoken words across ALL scenes <= "
                f"{int(round(total_target * _WORDS_PER_SECOND_SPOKEN))}. If a "
                "line exceeds budget: cut words, never impact."
            )

        # ── 6. Audio/Voice Style (forward-compat directives) ─────────
        if profile.preserve_audio_style and dna.audio_dna is not None:
            ad = dna.audio_dna
            sections.append(
                "AUDIO STYLE (PRESERVE): sound design "
                f"{'with' if ad.has_bgm else 'without'} background music"
                f"{f' ({ad.music_mood})' if ad.music_mood else ''}, SFX density {ad.sfx_density}."
            )
        if profile.preserve_voice_style:
            sections.append(
                "VOICE STYLE (PRESERVE): match the narrator tempo and delivery "
                "cadence of the source performance style."
            )

        # ── 7. Trend / Structure (timings only — never plot prose) ───
        if intent.story_mode == StoryMode.TREND_INSPIRED or profile.preserve_trend_structure:
            td = dna.trend_dna
            hook_line = (
                f"Viral hook formula: {td.viral_hook_type} | content format: "
                f"{td.content_format} | pacing archetype: {td.pacing_archetype}."
                if td is not None else
                "Apply a proven viral hook formula with rapid retention pacing."
            )
            sections.append("TREND INSPIRED (PRESERVE HOOK FORMULA):\n" + hook_line)
            timing_table = _beat_timing_table(source_dna)
            if timing_table:
                sections.append(
                    "TREND BEAT TIMINGS (structure only - do NOT copy plot "
                    "or dialogue):\n" + timing_table
                )
            sections.append(_wow_moment_clause(source_dna, exact=True))
        elif intent.story_mode == StoryMode.STRUCTURE_INSPIRED:
            ns = dna.narrative_structure_dna
            if ns is not None and ns.beat_types:
                sections.append(
                    "STRUCTURE-INSPIRED BEAT TIMINGS (structure only - do NOT "
                    "copy plot or dialogue):\n"
                    f"- Total beats: {ns.total_beats}\n"
                    f"- Beat types: {ns.beat_types}\n"
                    f"- Climax position: ~{ns.climax_position_percent}% of runtime\n"
                    + _beat_timing_table(source_dna)
                )
            else:
                sections.append(
                    "STRUCTURE POLICY: invent an original beat structure for "
                    "the new story."
                )
            sections.append(_wow_moment_clause(source_dna, exact=True))
        else:
            sections.append(
                "STORY POLICY - ORIGINAL VIRAL NARRATIVE (HIGH STAKES):\n"
                "Invent an entirely original beat structure; do not mirror "
                "the source timeline.\n"
                + _wow_moment_clause(source_dna, exact=False)
            )

        # ── 8. Strict rules & output contract ────────────────────────
        sections.append(
            "STRICT RULES - ZERO TOLERANCE:\n"
            "1. DO NOT reproduce ANY dialogue, action, gag, or punchline from "
            "the source video. Narrative similarity MUST stay far below 0.40 "
            "or the output is auto-rejected by the Originality Validator.\n"
            "2. Output STRICTLY valid JSON conforming to the ProductionBlueprint "
            "schema - no markdown, no commentary, JSON only.\n"
            "3. Divide the story into 3-5 cohesive scenes of 3-8 seconds each, "
            "summing to approximately the target duration.\n"
            f"4. All dialogue and narration MUST be in {ci.language}.\n"
            "5. VEO CINEMATOGRAPHY CONTRACT: every scene's action/"
            "visual_action field MUST carry 25-60 words of film-grade "
            "description covering subject + physical action + environment + "
            "lighting + camera motion/lens + emotion. Write for the video "
            "model, not a reader - this text IS the render brief.\n"
            "6. Maintain ONE consistent CINEMATIC VISUAL METAPHOR across all "
            "scenes; escalate it monotonically into the WOW MOMENT.\n"
            "7. Retention curve: highest-stakes image first (3-SECOND RULE), "
            "curiosity loop open by scene 2, WOW MOMENT payoff, clean button "
            "ending."
        )

        return "\n\n".join(sections)

