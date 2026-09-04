from collections import defaultdict
from .models import Alert,AlertIn,Quote,utcnow
class AlertEngine:
 def __init__(self):self.items=defaultdict(list);self.events=defaultdict(list)
 def create(self,user,body:AlertIn):
  row=Alert(user_id=user,**body.model_dump());self.items[user].append(row);return row
 def delete(self,user,alert_id):
  before=len(self.items[user]);self.items[user]=[x for x in self.items[user] if str(x.id)!=str(alert_id)];return len(self.items[user])<before
 def evaluate(self,user,quote:Quote):
  events=[]
  for a in self.items[user]:
   if a.instrument_id!=quote.instrument_id or a.state=="paused":continue
   value=quote.price if a.field=="price" else quote.change_pct if a.field=="change_pct" else quote.volume
   hit=value is not None and (value>a.target if a.operator=="above" else value<a.target)
   was_hit=a.state=="triggered"
   a.last_value=value
   if hit and not was_hit:
    a.state="triggered";a.last_triggered_at=utcnow();event={"id":str(a.id),"instrument_id":a.instrument_id,"field":a.field,"value":value,"target":a.target,"triggered_at":a.last_triggered_at};self.events[user].append(event);events.append(event)
   elif not hit and was_hit:a.state="armed"
  return events
 def evaluate_snapshot(self,user,instrument_id,snapshot):
  events=[]
  for a in self.items[user]:
   if a.instrument_id!=instrument_id or a.field not in snapshot or a.state=="paused":continue
   value=snapshot.get(a.field);hit=value is not None and (value>a.target if a.operator=="above" else value<a.target);was=a.state=="triggered";a.last_value=value
   if hit and not was:
    a.state="triggered";a.last_triggered_at=utcnow();event={"id":str(a.id),"instrument_id":a.instrument_id,"field":a.field,"value":value,"target":a.target,"triggered_at":a.last_triggered_at};self.events[user].append(event);events.append(event)
   elif not hit and was:a.state="armed"
  return events
alerts=AlertEngine()
