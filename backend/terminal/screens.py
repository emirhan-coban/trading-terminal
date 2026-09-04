from collections import defaultdict
from .models import SavedScreen,SavedScreenIn
class ScreenStore:
 def __init__(self):self.items=defaultdict(list)
 def create(self,user,body:SavedScreenIn):row=SavedScreen(user_id=user,**body.model_dump());self.items[user].append(row);return row
 def delete(self,user,row_id):
  before=len(self.items[user]);self.items[user]=[x for x in self.items[user] if str(x.id)!=str(row_id)];return before>len(self.items[user])
screens=ScreenStore()
