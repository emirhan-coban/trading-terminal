from collections import defaultdict
from .models import Workspace,WorkspaceIn,utcnow
DEFAULTS=[("Day Trading",["watch","chart","ticket","positions","flow"]),("Piyasa Genel",["watch","chart","flow","positions","ticket"]),("Şirket Araştırma",["watch","chart","flow","positions","ticket"]),("Portföy",["positions","chart","watch","flow","ticket"])]
class WorkspaceStore:
 def __init__(self):self.items=defaultdict(list)
 def defaults(self,user):
  if not self.items[user]:self.items[user]=[Workspace(user_id=user,name=name,layout={"panels":panels},is_default=n==0) for n,(name,panels) in enumerate(DEFAULTS)]
  return self.items[user]
 def save(self,user,body:WorkspaceIn):
  row=Workspace(user_id=user,**body.model_dump());self.items[user].append(row);return row
 def update(self,user,row_id,body:WorkspaceIn):
  for n,row in enumerate(self.items[user]):
   if str(row.id)==str(row_id):updated=Workspace(id=row.id,user_id=user,updated_at=utcnow(),**body.model_dump());self.items[user][n]=updated;return updated
  return None
workspaces=WorkspaceStore()
