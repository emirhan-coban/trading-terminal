from terminal.models import SavedScreenIn
from terminal.screens import ScreenStore
def test_saved_screen_round_trip():
 store=ScreenStore();row=store.create("u",SavedScreenIn(name="Momentum",filters={"asset_class":"crypto","min_rsi":50}));assert row.filters["asset_class"]=="crypto";assert store.delete("u",row.id)
