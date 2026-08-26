import uuid
from typing import List

from core.models.source_analysis import SourceAnalysis
from core.models.clone_blueprint import (
    CloneBlueprint, 
    CloneSceneBlueprint, 
    CloneShot, 
    NarrativeBeat, 
    PacingProfile
)

class CloneBlueprintBuilder:
    def __init__(self):
        pass

    def build_from_source(
        self, 
        source_analysis: SourceAnalysis,
        project_id: str,
        user_id: str,
        title: str = "Cloned Blueprint"
    ) -> CloneBlueprint:
        
        # We need a new ID for the CloneBlueprint
        blueprint_id = f"cl_{uuid.uuid4().hex[:12]}"
        
        # 1. Pacing Profile
        pacing_profile = self._build_pacing_profile(source_analysis)
        
        # 2. Scenes and Shots
        scenes = self._build_scenes(source_analysis)
        
        # 3. Narrative Structure (Basic default conversion if not explicitly modeled in SourceAnalysis)
        # Assuming the Hook Analysis provides the first beat, and CTA the last.
        narrative_structure = self._build_narrative_structure(source_analysis)
        
        return CloneBlueprint(
            clone_blueprint_id=blueprint_id,
            source_video_id=source_analysis.source_video_id,
            project_id=project_id,
            user_id=user_id,
            clone_blueprint_version=1,
            source_analysis_version=source_analysis.analyzer_version,
            title=title,
            source_duration_seconds=source_analysis.media_metadata.duration_seconds,
            target_duration_seconds=source_analysis.media_metadata.duration_seconds,
            aspect_ratio=source_analysis.media_metadata.aspect_ratio,
            hook=source_analysis.hook,
            narrative_structure=narrative_structure,
            pacing_profile=pacing_profile,
            visual_style_profile=source_analysis.visual_style,
            audio_profile=source_analysis.audio_profile,
            cta_structure=source_analysis.cta,
            scenes=scenes,
            status="DRAFT",
            analyzer_version="1.0.0"
        )
        
    def _build_pacing_profile(self, source_analysis: SourceAnalysis) -> PacingProfile:
        total_shots = len(source_analysis.scenes)
        if total_shots == 0:
            return PacingProfile(
                overall_intensity="LOW",
                average_shot_duration=source_analysis.media_metadata.duration_seconds,
                fastest_shot_duration=source_analysis.media_metadata.duration_seconds,
                slowest_shot_duration=source_analysis.media_metadata.duration_seconds,
                scene_count=1,
                shot_count=1,
                rhythm_description="Single continuous shot"
            )
            
        durations = [s.duration_seconds for s in source_analysis.scenes]
        avg = sum(durations) / len(durations)
        fastest = min(durations)
        slowest = max(durations)
        
        # Rough intensity heuristic
        if avg < 2.0:
            intensity = "HIGH"
        elif avg < 4.0:
            intensity = "MEDIUM"
        else:
            intensity = "LOW"
            
        return PacingProfile(
            overall_intensity=intensity,
            average_shot_duration=round(avg, 3),
            fastest_shot_duration=fastest,
            slowest_shot_duration=slowest,
            scene_count=len(source_analysis.semantic_scenes) if source_analysis.semantic_scenes else 1,
            shot_count=total_shots,
            rhythm_description=f"{intensity} pacing with {total_shots} shots averaging {round(avg, 1)}s"
        )

    def _build_scenes(self, source_analysis: SourceAnalysis) -> List[CloneSceneBlueprint]:
        # SourceAnalysis mapped semantics 1:1 to cuts. 
        # But conceptually, a "Scene" might have multiple shots.
        # Since Phase 8A mapped 1 cut = 1 semantic scene, we will treat each cut as a Shot,
        # but group them into Scenes based on Narrative Purpose or Location if possible.
        # For simplicity in 8B, we preserve 1:1 but structure it properly.
        
        scenes_out: List[CloneSceneBlueprint] = []
        
        for i, segment in enumerate(source_analysis.scenes):
            # Find matching semantic scene
            sem = next((s for s in source_analysis.semantic_scenes if s.scene_number == segment.scene_number), None)
            
            if not sem:
                continue
                
            # Create a shot for this segment
            shot = CloneShot(
                shot_number=1,
                source_start_seconds=segment.start_seconds,
                source_end_seconds=segment.end_seconds,
                duration_seconds=segment.duration_seconds,
                shot_type=sem.shot_type,
                camera_motion=sem.camera_motion,
                framing=None,
                lens_description=None,
                camera_angle=None,
                composition=None,
                visual_action=sem.visual_action,
                transition=sem.transition
            )
            
            scene = CloneSceneBlueprint(
                scene_id=f"scn_{uuid.uuid4().hex[:8]}",
                scene_number=segment.scene_number,
                source_start_seconds=segment.start_seconds,
                source_end_seconds=segment.end_seconds,
                source_duration_seconds=segment.duration_seconds,
                narrative_purpose=sem.narrative_purpose,
                visual_action=sem.visual_action,
                dialogue_intent=sem.dialogue_intent,
                emotion=sem.emotion,
                pacing=sem.pacing_intensity,
                shot_sequence=[shot],
                character_roles=sem.character_roles,
                location_summary=sem.location_summary,
                prop_summary=sem.prop_summary,
                lighting_summary=sem.lighting_summary,
                transition=sem.transition,
                audio_structure=None
            )
            scenes_out.append(scene)
            
        return scenes_out
        
    def _build_narrative_structure(self, source_analysis: SourceAnalysis) -> List[NarrativeBeat]:
        beats = []
        # Add Hook Beat
        if source_analysis.hook.hook_type != "NONE" and source_analysis.hook.hook_start_seconds is not None:
            beats.append(NarrativeBeat(
                type="HOOK",
                start_seconds=source_analysis.hook.hook_start_seconds,
                end_seconds=source_analysis.hook.hook_end_seconds or source_analysis.hook.hook_start_seconds + 3.0,
                description=source_analysis.hook.hook_description or "Hook",
                importance="HIGH"
            ))
            
        # Add CTA Beat
        if source_analysis.cta.exists and source_analysis.cta.start_seconds is not None:
            beats.append(NarrativeBeat(
                type="CTA",
                start_seconds=source_analysis.cta.start_seconds,
                end_seconds=source_analysis.cta.end_seconds or source_analysis.media_metadata.duration_seconds,
                description=source_analysis.cta.description or "Call to Action",
                importance="HIGH"
            ))
            
        return beats
