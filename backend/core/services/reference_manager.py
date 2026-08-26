import uuid
import datetime
from typing import Optional
from pydantic import BaseModel

from core.models.context import GenerationContext
from core.services.bible_loader import ResolvedScene
from core.models.character_asset import CharacterAsset
from core.firestore_client import get_db
from core.models.operation_state import OperationStatus, ErrorCategory
from core.exceptions import CharacterReferenceError

class ReferenceResolutionResult(BaseModel):
    reference_uri: Optional[str] = None
    reference_requested: bool = True
    reference_required: bool = True
    status: OperationStatus = OperationStatus.NOT_REQUESTED
    reference_source: str = "NONE"  # "PROJECT_BIBLE", "CHARACTER_ASSET", "CACHE", "GENERATED_ASSET", "FALLBACK"
    reference_asset_id: Optional[str] = None
    reference_generation_attempted: bool = False
    reference_generation_status: Optional[str] = None  # "SUCCESS", "FAILED", "SKIPPED", "NOT_REQUESTED"
    reference_validation_status: Optional[str] = None  # "VALID", "INVALID", "BYPASSED", "NOT_REQUESTED"
    reference_failure_reason: Optional[str] = None
    error_type: ErrorCategory = ErrorCategory.NONE
    fallback_used: bool = False
    fallback_mode: Optional[str] = None  # "PROMPT_ONLY", "CANONICAL_FALLBACK", None
    character_id: str = "default"

class ReferenceManager:
    def __init__(self):
        self.db = get_db()

    def validate_reference_uri(self, uri: Optional[str], context: Optional[GenerationContext] = None) -> bool:
        """
        Validates the format, scheme, and project ownership of a reference URI.
        """
        if not uri or not isinstance(uri, str):
            return False
            
        uri_clean = uri.strip()
        if not uri_clean:
            return False
            
        # Must have a valid URI scheme
        if not (uri_clean.startswith("gs://") or uri_clean.startswith("https://") or uri_clean.startswith("http://")):
            print(f"[ReferenceManager] REFERENCE_VALIDATION_FAILED: Invalid URI scheme in '{uri_clean}'")
            return False
            
        # Cross-tenant check for GCS paths: if context is provided, ensure user cannot use another user's path
        if context and uri_clean.startswith("gs://") and "users/" in uri_clean:
            expected_prefix = f"users/{context.user_id}/"
            if expected_prefix not in uri_clean and "assets/" not in uri_clean:
                print(f"[ReferenceManager] SECURITY_VALIDATION_FAILED: URI '{uri_clean}' does not belong to user {context.user_id}")
                return False

        return True

    def resolve_reference_with_telemetry(
        self,
        context: GenerationContext,
        resolved_scene: ResolvedScene,
        target_character_id: Optional[str] = None,
        reference_required: Optional[bool] = None,
        allow_fallback: bool = True
    ) -> ReferenceResolutionResult:
        primary_character = resolved_scene.characters[0] if resolved_scene.characters else None
        char_id = target_character_id or (primary_character.character_id if primary_character else "default")
        
        if reference_required is None:
            reference_required = bool(
                (resolved_scene and resolved_scene.characters) or 
                target_character_id or 
                (context.metadata and context.metadata.get("character_design"))
            )


        result = ReferenceResolutionResult(
            reference_requested=reference_required,
            reference_required=reference_required,
            character_id=char_id,
            status=OperationStatus.STARTED if reference_required else OperationStatus.NOT_REQUESTED
        )
        
        if not reference_required:
            result.status = OperationStatus.NOT_REQUESTED
            result.reference_generation_status = "NOT_REQUESTED"
            result.reference_validation_status = "NOT_REQUESTED"
            result.fallback_mode = "PROMPT_ONLY"
            return result

        # Initialize context cache if needed
        if context.metadata is None:
            context.metadata = {}
        if "reference_cache" not in context.metadata:
            context.metadata["reference_cache"] = {}

        selected_uri = None
        source_tag = "NONE"
        asset_id = None

        # -------------------------------------------------------------
        # STEP 0: Check VisualIdentityPack (Master Sheet & Shot-Aware Panels)
        # -------------------------------------------------------------
        camera_val = getattr(resolved_scene.scene, "camera", None)
        camera = ""
        if camera_val:
            if hasattr(camera_val, "model_dump"):
                dumped = camera_val.model_dump()
                camera = " ".join(str(v) for v in dumped.values() if v).lower()
            elif hasattr(camera_val, "value"):
                camera = str(camera_val.value).lower()
            else:
                camera = str(camera_val).lower()

        vip = context.metadata.get("visual_identity_pack") if context.metadata else None
        if not vip and self.db:
            try:
                from core.repositories.visual_identity_repo import VisualIdentityRepository
                vip_repo = VisualIdentityRepository()
                vip = vip_repo.get_latest(context.user_id, context.project_id)
                if vip and context.metadata is not None:
                    context.metadata["visual_identity_pack"] = vip
            except Exception as e:
                print(f"[ReferenceManager] VisualIdentityPack lookup warning: {e}")

        if vip and hasattr(vip, "characters") and char_id in vip.characters:
            cvi = vip.characters[char_id]
            cand = None
            if "close-up" in camera or "portrait" in camera or "closeup" in camera:
                cand = cvi.closeup_ref_uri or cvi.front_ref_uri
            elif "side" in camera or "profile" in camera:
                cand = cvi.side_ref_uri or cvi.three_quarter_left_uri or cvi.front_ref_uri
            elif "back" in camera or "rear" in camera or "over_shoulder" in camera:
                cand = cvi.back_ref_uri or cvi.front_ref_uri
            elif "full" in camera or "wide" in camera or "establish" in camera:
                cand = cvi.full_body_ref_uri or cvi.three_quarter_left_uri or cvi.master_sheet_uri or cvi.front_ref_uri
            else:
                cand = cvi.front_ref_uri or cvi.three_quarter_left_uri or cvi.master_sheet_uri

            if cand and self.validate_reference_uri(cand, context):
                selected_uri = cand
                source_tag = "VISUAL_IDENTITY_PACK"
                print(f"[ReferenceManager] Resolved shot-aware reference from VisualIdentityPack for {char_id} (camera='{camera}'): {selected_uri}")

        # -------------------------------------------------------------
        # STEP 1: Check Camera-Specific CharacterAssets in Firestore
        # -------------------------------------------------------------
        if not selected_uri:
            desired_type = None
            if "close-up" in camera or "portrait" in camera:
                desired_type = "front_portrait"
            elif "side" in camera or "profile" in camera:
                desired_type = "side_profile"
            elif "full" in camera or "wide" in camera:
                desired_type = "full_body"

            if desired_type and primary_character and self.db:
                try:
                    docs = self.db.collection("users").document(context.user_id)\
                                  .collection("projects").document(context.project_id)\
                                  .collection("character_assets")\
                                  .where("character_id", "==", char_id)\
                                  .where("asset_type", "==", desired_type)\
                                  .limit(1).stream()
                    for doc in docs:
                        d_data = doc.to_dict()
                        storage_uri = d_data.get("storage_uri")
                        if self.validate_reference_uri(storage_uri, context):
                            selected_uri = storage_uri
                            source_tag = "CHARACTER_ASSET"
                            asset_id = doc.id
                            break
                except Exception as e:
                    print(f"[ReferenceManager] Firestore CharacterAsset query warning: {e}")

        # -------------------------------------------------------------
        # STEP 2: Check Canonical Reference on Project Bible Character
        # -------------------------------------------------------------
        if not selected_uri and primary_character and primary_character.canonical_reference_uri:
            cand_uri = primary_character.canonical_reference_uri
            if self.validate_reference_uri(cand_uri, context):
                selected_uri = cand_uri
                source_tag = "PROJECT_BIBLE"

        # -------------------------------------------------------------
        # STEP 3: Check Memory Cache in GenerationContext
        # -------------------------------------------------------------
        if not selected_uri and "reference_cache" in context.metadata:
            cache = context.metadata["reference_cache"]
            if char_id in cache:
                cand_uri = cache[char_id]
                if self.validate_reference_uri(cand_uri, context):
                    selected_uri = cand_uri
                    source_tag = "CACHE"
                    print(f"[ReferenceManager] Reusing cached reference for {char_id}: {selected_uri}")
            elif char_id == "default" and "default" in cache:
                cand_uri = cache["default"]
                if self.validate_reference_uri(cand_uri, context):
                    selected_uri = cand_uri
                    source_tag = "CACHE"
                    print(f"[ReferenceManager] Reusing default cached reference: {selected_uri}")

        # -------------------------------------------------------------
        # STEP 4: Generate Canonical Reference Asset (If Missing)
        # -------------------------------------------------------------
        if not selected_uri:
            print(f"[ReferenceManager] No canonical or cached reference found for {char_id}. Generating reference...")
            result.reference_generation_attempted = True
            
            try:
                from services.asset_generator import generate_character_reference
                
                art_style = context.metadata.get("art_style", "") if context.metadata else ""
                legacy_design = primary_character.legacy_character_design if primary_character else None
                character_design = legacy_design or (context.metadata.get("character_design") if context.metadata else None) or "3D character"
                
                subject = f"{art_style}, {character_design}".strip(", ")
                gen_uri = generate_character_reference(
                    subject,
                    user_id=context.user_id,
                    project_id=context.project_id,
                    character_id=char_id
                )
                
                if gen_uri and self.validate_reference_uri(gen_uri, context):
                    selected_uri = gen_uri
                    source_tag = "GENERATED_ASSET"
                    result.reference_generation_status = "SUCCESS"
                    
                    # Persist newly generated asset record in Firestore
                    if self.db:
                        try:
                            asset_doc_id = f"charref_{uuid.uuid4().hex[:12]}"
                            asset_obj = CharacterAsset(
                                asset_id=asset_doc_id,
                                character_id=char_id,
                                asset_type=desired_type or "front_portrait",
                                storage_uri=gen_uri,
                                metadata={"prompt": subject},
                                created_at=datetime.datetime.now(datetime.timezone.utc)
                            )
                            self.db.collection("users").document(context.user_id)\
                                   .collection("projects").document(context.project_id)\
                                   .collection("character_assets").document(asset_doc_id)\
                                   .set(asset_obj.model_dump())
                            asset_id = asset_doc_id
                            
                            # Also update Character bible document if exists
                            if primary_character and primary_character.character_id != "default":
                                self.db.collection("users").document(context.user_id)\
                                       .collection("projects").document(context.project_id)\
                                       .collection("characters").document(primary_character.character_id)\
                                       .set({"canonical_reference_uri": gen_uri}, merge=True)
                        except Exception as save_err:
                            print(f"[ReferenceManager] Failed to persist generated asset document: {save_err}")
                            
                    # Cache in Context under its specific character ID
                    context.metadata["reference_cache"][char_id] = gen_uri
                    if "default" not in context.metadata["reference_cache"]:
                        context.metadata["reference_cache"]["default"] = gen_uri
                    print(f"[ReferenceManager] Cached new reference for {char_id}: {gen_uri}")
                else:
                    result.reference_generation_status = "FAILED"
                    result.reference_failure_reason = "Image generation provider returned empty or invalid URI"
                    result.error_type = ErrorCategory.REFERENCE_GENERATION_FAILED
                    result.status = OperationStatus.FAILED
            except Exception as gen_err:
                print(f"[ReferenceManager ERROR] Reference generation failed: {gen_err}")
                result.reference_generation_status = "FAILED"
                result.reference_failure_reason = str(gen_err)
                result.error_type = ErrorCategory.REFERENCE_GENERATION_FAILED
                result.status = OperationStatus.FAILED

        # -------------------------------------------------------------
        # STEP 5: Final Validation & Telemetry Population
        # -------------------------------------------------------------
        if selected_uri:
            if self.validate_reference_uri(selected_uri, context):
                result.reference_uri = selected_uri
                result.reference_source = source_tag
                result.reference_asset_id = asset_id
                result.reference_validation_status = "VALID"
                result.status = OperationStatus.SUCCEEDED
                result.fallback_mode = None
                result.error_type = ErrorCategory.NONE
            else:
                result.reference_uri = None
                result.reference_validation_status = "INVALID"
                result.reference_failure_reason = f"Reference URI '{selected_uri}' failed validation"
                result.error_type = ErrorCategory.REFERENCE_VALIDATION_FAILED
                result.status = OperationStatus.FAILED
        else:
            result.reference_uri = None
            if not result.reference_failure_reason:
                result.reference_failure_reason = "No reference available"
            if result.error_type == ErrorCategory.NONE:
                result.error_type = ErrorCategory.REFERENCE_GENERATION_FAILED
            result.status = OperationStatus.FAILED

        # Fail-closed check
        if reference_required and result.status == OperationStatus.FAILED:
            if allow_fallback:
                result.fallback_used = True
                result.fallback_mode = "PROMPT_ONLY"
                result.status = OperationStatus.FALLBACK_USED
            else:
                # Strictly fail closed
                raise CharacterReferenceError(
                    f"Required character reference resolution failed for '{char_id}': {result.reference_failure_reason}",
                    details=result.model_dump()
                )
        elif not reference_required and result.status == OperationStatus.FAILED:
            result.fallback_mode = "PROMPT_ONLY"

        return result

    def get_reference_uri(self, context: GenerationContext, resolved_scene: ResolvedScene) -> Optional[str]:
        """
        Legacy-compatible convenience method. Resolves the reference and returns the URI string.
        """
        res = self.resolve_reference_with_telemetry(context, resolved_scene, reference_required=True, allow_fallback=True)
        return res.reference_uri

