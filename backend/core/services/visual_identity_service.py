"""
Visual Identity Service
=======================
Coordinates generation, extraction, persistence, and version locking of
VisualIdentityPack, CharacterVisualIdentity multi-angle sheets,
EnvironmentVisualIdentity, and PropVisualIdentity.
"""
import uuid
import datetime
from typing import Optional, List, Dict, Any

from core.models.visual_identity import (
    VisualIdentityPack,
    CharacterVisualIdentity,
    EnvironmentVisualIdentity,
    PropVisualIdentity,
    VisualTreatment
)
from core.repositories.visual_identity_repo import VisualIdentityRepository
from core.repositories.character_repo import CharacterRepository
from services.asset_generator import generate_character_reference
from services.trend_remixer import _sanitize_veo_prompt

class VisualIdentityService:
    def __init__(self):
        self.vip_repo = VisualIdentityRepository()
        self.char_repo = CharacterRepository()

    def build_or_get_visual_identity_pack(
        self,
        user_id: str,
        project_id: str,
        art_style: str = "3D Pixar-style digital animation",
        character_design: str = "3D animated characters",
        characters: Optional[List[Dict[str, Any]]] = None,
        environments: Optional[List[Dict[str, Any]]] = None,
        props: Optional[List[Dict[str, Any]]] = None
    ) -> VisualIdentityPack:
        """
        Retrieves existing locked VisualIdentityPack, or generates a new
        authoritative multi-angle reference sheet and persists it.
        """
        existing = self.vip_repo.get_latest(user_id, project_id)
        if existing and existing.status in ("APPROVED", "LOCKED"):
            # Check if the existing VIP matches the requested style.
            # If the user uploaded a new video with a different visual style,
            # we must NOT return the stale locked VIP from a previous video.
            existing_art = getattr(existing.visual_treatment, 'art_style', '') if existing.visual_treatment else ''
            styles_match = (
                not art_style
                or not existing_art
                or art_style.lower().strip() == existing_art.lower().strip()
            )
            
            # Check if character design matches
            existing_char_design = ""
            if existing.characters:
                first_char = next(iter(existing.characters.values()))
                existing_char_design = first_char.visual_descriptor
            
            # Since visual_descriptor has art_style embedded, we just check if the new design text is in it
            char_design_match = (
                not character_design
                or not existing_char_design
                or character_design.lower().strip() in existing_char_design.lower().strip()
            )

            if styles_match and char_design_match:
                return existing
            else:
                print(f"[VIP] Existing VIP doesn't match requested style/design. Generating new VIP.")

        pack_id = f"vip_{uuid.uuid4().hex[:8]}"
        treatment = VisualTreatment(
            art_style=art_style,
            lighting="Cinematic subsurface lighting, vibrant colors",
            render_language="3D digital render, volumetric illumination",
            texture_rules="Clean metallic, fabric, and stylized surfaces"
        )

        char_identities: Dict[str, CharacterVisualIdentity] = {}
        raw_char_list = characters or [{"character_id": "char_primary", "name": "Primary Character"}]
        char_list = []
        for c in raw_char_list:
            if isinstance(c, str):
                char_list.append({"character_id": f"char_{uuid.uuid4().hex[:6]}", "name": c})
            elif isinstance(c, dict):
                char_list.append(c)
            else:
                char_list.append({"character_id": f"char_{uuid.uuid4().hex[:6]}", "name": str(c)})

        for c_data in char_list:
            cid = c_data.get("character_id", f"char_{uuid.uuid4().hex[:6]}")
            c_name = c_data.get("name", "Character")
            
            # Check if Character model already has canonical reference
            c_obj = self.char_repo.get(user_id, project_id, cid)
            existing_ref = c_obj.canonical_reference_uri if c_obj else None

            if existing_ref:
                cvi = CharacterVisualIdentity(
                    character_id=cid,
                    project_id=project_id,
                    name=c_name,
                    version=1,
                    master_sheet_uri=existing_ref,
                    front_ref_uri=existing_ref,
                    three_quarter_left_uri=existing_ref,
                    three_quarter_right_uri=existing_ref,
                    closeup_ref_uri=existing_ref,
                    full_body_ref_uri=existing_ref,
                    visual_descriptor=f"{art_style}, {character_design}",
                    status="APPROVED"
                )
            else:
                # Generate multi-angle model sheet prompt
                sheet_prompt = (
                    f"Character sheet of {c_name}, {character_design}, {art_style}. "
                    f"Multiple angles including front view, 3/4 view, side profile, and full body turnaround. "
                    f"Clean neutral background, studio lighting, highly detailed 3D render."
                )
                sheet_prompt = _sanitize_veo_prompt(sheet_prompt, art_style=art_style, character_design=character_design, is_animated=True)
                
                sheet_uri = generate_character_reference(
                    character_desc=sheet_prompt,
                    user_id=user_id,
                    project_id=project_id,
                    character_id=cid
                )

                cvi = CharacterVisualIdentity(
                    character_id=cid,
                    project_id=project_id,
                    name=c_name,
                    version=1,
                    master_sheet_uri=sheet_uri,
                    front_ref_uri=sheet_uri,
                    three_quarter_left_uri=sheet_uri,
                    three_quarter_right_uri=sheet_uri,
                    closeup_ref_uri=sheet_uri,
                    full_body_ref_uri=sheet_uri,
                    visual_descriptor=sheet_prompt,
                    status="APPROVED"
                )

                # Also update Character repository canonical reference
                if c_obj:
                    c_obj.canonical_reference_uri = sheet_uri
                    self.char_repo.save(user_id, project_id, cid, c_obj)
                else:
                    from core.models.character import Character
                    new_char = Character(
                        character_id=cid,
                        project_id=project_id,
                        name=c_name,
                        canonical_reference_uri=sheet_uri
                    )
                    self.char_repo.save(user_id, project_id, cid, new_char)

            char_identities[cid] = cvi

        # Environment references
        env_identities: Dict[str, EnvironmentVisualIdentity] = {}
        if environments:
            for env in environments:
                if isinstance(env, str):
                    env = {"environment_id": f"env_{uuid.uuid4().hex[:6]}", "name": env}
                eid = env.get("environment_id", f"env_{uuid.uuid4().hex[:6]}")
                ename = env.get("name", "Main Setting")
                e_uri = env.get("canonical_uri", char_identities[list(char_identities.keys())[0]].front_ref_uri or "")
                env_identities[eid] = EnvironmentVisualIdentity(
                    environment_id=eid,
                    project_id=project_id,
                    name=ename,
                    version=1,
                    canonical_uri=e_uri,
                    lighting_descriptor="Natural cinematic daylight",
                    status="APPROVED"
                )

        # Prop references
        prop_identities: Dict[str, PropVisualIdentity] = {}
        if props:
            for p in props:
                if isinstance(p, str):
                    p = {"prop_id": f"prop_{uuid.uuid4().hex[:6]}", "name": p}
                pid = p.get("prop_id", f"prop_{uuid.uuid4().hex[:6]}")
                pname = p.get("name", "Key Item")
                p_uri = p.get("canonical_uri", "")
                prop_identities[pid] = PropVisualIdentity(
                    prop_id=pid,
                    project_id=project_id,
                    name=pname,
                    version=1,
                    canonical_uri=p_uri,
                    visual_descriptor=f"Detailed 3D model of {pname}",
                    status="APPROVED"
                )

        pack = VisualIdentityPack(
            pack_id=pack_id,
            project_id=project_id,
            version=1,
            characters=char_identities,
            environments=env_identities,
            props=prop_identities,
            visual_treatment=treatment,
            status="APPROVED"
        )

        self.vip_repo.save(user_id, project_id, pack_id, pack)
        return pack
