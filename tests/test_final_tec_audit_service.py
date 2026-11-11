from types import SimpleNamespace
from final_tec_audit_service import append_authenticated_audit_event
class Auth:
 def __init__(self,uid): self.uid=uid; self.calls=0
 def get_user(self): self.calls+=1; return SimpleNamespace(user=SimpleNamespace(id=self.uid))
class Rpc:
 def __init__(self,data=None,error=None): self.data=data; self.error=error; self.name=None; self.params=None
 def execute(self):
  if self.error: raise self.error
  return SimpleNamespace(data=self.data)
class Server:
 def __init__(self,rpc): self.r=rpc
 def rpc(self,name,params): self.r.name=name; self.r.params=params; return self.r
def run(verified=None,action="investor_dashboard_viewed",reason="dashboard_view",data=None,error=None):
 uid="00000000-0000-0000-0000-000000000001"; auth=Auth(verified or uid)
 rpc=Rpc(data if data is not None else [{"sequence_id":1,"event_id":"e","event_hash":"a"*64,"occurred_at":"2026-11-11T10:00:00+00:00"}],error)
 result=append_authenticated_audit_event(user_client=SimpleNamespace(auth=auth),server_client=Server(rpc),
  authenticated_user=SimpleNamespace(id=uid),actor_role="final_tec_investor_viewer",action=action,
  resource_type="dashboard",resource_id="investor-live",outcome="allowed",reason_code=reason)
 return result,auth,rpc
def test_validated_identity_uses_narrow_rpc():
 result,auth,rpc=run(); assert result["sequence_id"]==1 and auth.calls==1
 assert rpc.name=="final_tec_append_audit_event" and rpc.params["p_actor_id"].endswith("0001")
def test_identity_mismatch_fails_closed():
 result,auth,rpc=run(verified="other"); assert result is None and auth.calls==1 and rpc.name is None
def test_role_action_mismatch_fails_closed():
 result,_,rpc=run(action="access_granted"); assert result is None and rpc.name is None
def test_freeform_reason_rejected():
 result,_,_=run(reason="email:user@example.com"); assert result is None
def test_malformed_receipt_and_rpc_error_fail_closed():
 assert run(data=[])[0] is None
 assert run(data=None,error=RuntimeError("db"))[0] is None
