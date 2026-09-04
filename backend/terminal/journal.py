from collections import defaultdict
from .models import JournalEntry,JournalEntryIn,utcnow
class JournalStore:
 def __init__(self):self.items=defaultdict(list)
 def create(self,user,body:JournalEntryIn):
  row=JournalEntry(user_id=user,**body.model_dump());self.items[user].append(row);return row
 def update(self,user,entry_id,body:JournalEntryIn):
  for i,row in enumerate(self.items[user]):
   if str(row.id)==str(entry_id):
    updated=JournalEntry(id=row.id,user_id=user,created_at=row.created_at,updated_at=utcnow(),**body.model_dump());self.items[user][i]=updated;return updated
  return None
 def delete(self,user,entry_id):
  before=len(self.items[user]);self.items[user]=[x for x in self.items[user] if str(x.id)!=str(entry_id)];return len(self.items[user])<before
journal=JournalStore()
