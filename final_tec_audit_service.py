"""Server-side FINAL TEC audit writer."""
from __future__ import annotations
import re
from typing import Any
from settings import get_setting

_ALLOWED_ROLE_ACTIONS = {
 "final_tec_admin":{"evidence_submitted","evidence_reviewed","evidence_changes_requested","evidence_rejected","evidence_publication_requested","evidence_published","evidence_unpublished","access_granted","access_revoked"},
 "final_tec_analyst":{"evidence_submitted","evidence_reviewed","evidence_changes_requested","evidence_rejected"},
 "final_tec_investor_viewer":{"investor_dashboard_viewed"},
}
_ALLOWED_OUTCOMES={"allowed","accepted","denied","pending","completed","failed"}
_REASON=re.compile(r"^[a-z0-9_.-]{3,80}$")

def create_server_audit_client() -> Any | None:
    """Create a server-only Supabase client; missing secret disables audit writes."""
    url=str(get_setting("SUPABASE_URL","")).strip()
    key=str(get_setting("SUPABASE_SERVICE_ROLE_KEY","")).strip()
    if not url.startswith("https://") or not key: return None
    from supabase import create_client
    return create_client(url,key)

def append_authenticated_audit_event(*,user_client:Any,server_client:Any,authenticated_user:Any,
    actor_role:str,action:str,resource_type:str,resource_id:str,outcome:str,reason_code:str) -> dict[str,Any] | None:
    """Revalidate identity and call only the restricted server RPC."""
    user_id=getattr(authenticated_user,"id",None)
    if not user_id or user_client is None or server_client is None: return None
    if actor_role not in _ALLOWED_ROLE_ACTIONS or action not in _ALLOWED_ROLE_ACTIONS[actor_role]: return None
    if outcome not in _ALLOWED_OUTCOMES: return None
    if not isinstance(resource_type,str) or not 1<=len(resource_type.strip())<=160: return None
    if not isinstance(resource_id,str) or not 1<=len(resource_id.strip())<=160: return None
    if not isinstance(reason_code,str) or not _REASON.fullmatch(reason_code): return None
    try:
        auth_response=user_client.auth.get_user()
        verified=getattr(auth_response,"user",auth_response)
        if str(getattr(verified,"id", ""))!=str(user_id): return None
        response=server_client.rpc("final_tec_append_audit_event",{
          "p_actor_id":str(user_id),"p_actor_role":actor_role,"p_action":action,
          "p_resource_type":resource_type.strip(),"p_resource_id":resource_id.strip(),
          "p_outcome":outcome,"p_reason_code":reason_code,
        }).execute()
        data=getattr(response,"data",None)
        receipt=data[0] if isinstance(data,list) and data and isinstance(data[0],dict) else data
        if not isinstance(receipt,dict): return None
        keys=("sequence_id","event_id","event_hash","occurred_at")
        if any(receipt.get(k) is None for k in keys): return None
        return {k:receipt[k] for k in keys}
    except Exception:
        return None
