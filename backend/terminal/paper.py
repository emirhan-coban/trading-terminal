from collections import defaultdict
from datetime import timedelta
from uuid import uuid4

from .catalog import catalog
from .models import Freshness, PaperOrder, PaperOrderIn, Position, Quote, utcnow


class PaperBroker:
    def __init__(self, starting_cash=100000):
        self.starting_cash = starting_cash
        self.cash = defaultdict(lambda: starting_cash)
        self.orders = defaultdict(list)
        self.holdings = defaultdict(dict)
        self.fills = defaultdict(list)
        self.cash_ledger = defaultdict(list)
        self.audit = defaultdict(list)
        self.excursions = defaultdict(dict)

    @staticmethod
    def _is_fresh(quote: Quote) -> bool:
        return (
            quote.price is not None
            and quote.freshness not in {Freshness.stale, Freshness.unavailable}
            and utcnow() - quote.as_of <= timedelta(minutes=20)
        )

    def _execute(self, user: str, order: PaperOrder, quote: Quote, quantity: float) -> bool:
        instrument = catalog.get(order.instrument_id)
        if not instrument or not self._is_fresh(quote):
            order.status, order.rejection_reason = "rejected", "STALE_MARKET_DATA"
            return False
        fill = quote.price * (1.0005 if order.side == "buy" else .9995)
        notional, fee = fill * quantity, max(.01, fill * quantity * .001)
        held, average = self.holdings[user].get(order.instrument_id, (0., 0.))
        if order.side == "buy" and notional + fee > self.cash[user]:
            order.status, order.rejection_reason = "rejected", "INSUFFICIENT_BUYING_POWER"
            return False
        if order.side == "sell" and quantity > held:
            order.status, order.rejection_reason = "rejected", "INSUFFICIENT_POSITION"
            return False
        if order.side == "buy":
            new_quantity = held + quantity
            average = ((held * average) + notional + fee) / new_quantity
            self.cash[user] -= notional + fee
            self.excursions[user][order.instrument_id] = {"entry":average,"mae":0.,"mfe":0.}
        else:
            new_quantity = held - quantity
            self.cash[user] += notional - fee
            order.realized_pnl = round((fill - average) * quantity - fee, 4)
            excursion=self.excursions[user].get(order.instrument_id)
            if excursion:order.mae=round(excursion["mae"],4);order.mfe=round(excursion["mfe"],4)
        if new_quantity:
            self.holdings[user][order.instrument_id] = (new_quantity, average)
        else:
            self.holdings[user].pop(order.instrument_id, None)
            self.excursions[user].pop(order.instrument_id,None)
        old_filled = order.filled_quantity
        total = old_filled + quantity
        order.fill_price = round(((order.fill_price or 0) * old_filled + fill * quantity) / total, instrument.price_precision)
        order.filled_quantity = total
        order.commission = round(order.commission + fee, 4)
        order.status = "filled" if total >= order.quantity else "partially_filled"
        order.updated_at = utcnow()
        self.fills[user].append({"id":str(uuid4()),"user_id":user,"account_id":order.account_id,"order_id":str(order.id),"instrument_id":order.instrument_id,"side":order.side,"quantity":quantity,"price":order.fill_price,"commission":round(fee,4),"filled_at":order.updated_at})
        self.cash_ledger[user].append({"id":str(uuid4()),"user_id":user,"account_id":order.account_id,"currency":instrument.quote_currency or instrument.currency,"amount":round(-(notional+fee) if order.side=="buy" else notional-fee,4),"event_type":"paper_fill","reference_id":str(order.id),"created_at":order.updated_at})
        self.audit[user].append({"id":str(uuid4()),"user_id":user,"event_type":"paper.fill","entity_id":str(order.id),"payload":{"status":order.status,"quantity":quantity,"price":order.fill_price},"created_at":order.updated_at})
        return True

    def _protective_children(self, user: str, parent: PaperOrder, request: PaperOrderIn):
        group = uuid4()
        exit_side = "sell" if request.side == "buy" else "buy"
        children = [
            PaperOrder(user_id=user, account_id=parent.account_id, instrument_id=parent.instrument_id,
                       side=exit_side, order_type="limit", quantity=request.quantity, status="accepted",
                       limit_price=request.take_profit, parent_id=parent.id, oco_group=group),
            PaperOrder(user_id=user, account_id=parent.account_id, instrument_id=parent.instrument_id,
                       side=exit_side, order_type="stop", quantity=request.quantity, status="accepted",
                       stop_price=request.stop_loss, parent_id=parent.id, oco_group=group),
        ]
        self.orders[user].extend(children)

    def submit(self, user, request: PaperOrderIn, quote: Quote):
        order = PaperOrder(user_id=user, account_id=f"paper:{user}", status="new",
                           **request.model_dump(exclude={"take_profit", "stop_loss"}))
        instrument = catalog.get(request.instrument_id)
        if not instrument:
            order.status, order.rejection_reason = "rejected", "UNKNOWN_INSTRUMENT"
        elif not self._is_fresh(quote):
            order.status, order.rejection_reason = "rejected", "STALE_MARKET_DATA"
        elif request.order_type == "oco":
            order.status = "accepted"
            self.orders[user].append(order)
            self._protective_children(user, order, request)
            return order
        elif request.order_type in {"limit", "stop", "stop_limit"}:
            order.status = "accepted"
        else:
            self._execute(user, order, quote, request.quantity)
        order.updated_at = utcnow()
        self.orders[user].append(order)
        self.audit[user].append({"id":str(uuid4()),"user_id":user,"event_type":"paper.order.created","entity_id":str(order.id),"payload":{"status":order.status,"type":order.order_type},"created_at":order.updated_at})
        if request.order_type == "bracket" and order.status == "filled":
            self._protective_children(user, order, request)
        return order

    def positions(self, user, quotes):
        out = []
        for iid, (qty, avg) in self.holdings[user].items():
            instrument, quote = catalog.get(iid), quotes.get(iid)
            last = quote.price if quote else None
            out.append(Position(instrument_id=iid, quantity=qty, average_price=avg, last_price=last,
                                market_value=last * qty if last is not None else None,
                                unrealized_pnl=(last - avg) * qty if last is not None else None,
                                currency=instrument.quote_currency or instrument.currency,
                                freshness=quote.freshness if quote else Freshness.unavailable))
        return out

    def cancel(self, user, order_id):
        for order in self.orders[user]:
            if str(order.id) == str(order_id) and order.status in {"new", "accepted", "partially_filled"}:
                order.status, order.updated_at = "cancelled", utcnow()
                self.audit[user].append({"id":str(uuid4()),"user_id":user,"event_type":"paper.order.cancelled","entity_id":str(order.id),"payload":{},"created_at":order.updated_at})
                for sibling in self.orders[user]:
                    if order.order_type == "oco" and sibling.parent_id == order.id and sibling.status == "accepted":
                        sibling.status, sibling.updated_at = "cancelled", utcnow()
                return order
        return None

    def process(self, user, quote, available_quantity: float | None = None):
        """Fill resting orders and atomically cancel the other OCO leg."""
        changed = []
        if not self._is_fresh(quote):
            return changed
        excursion=self.excursions[user].get(quote.instrument_id)
        if excursion and excursion["entry"]:
            move=(quote.price/excursion["entry"]-1)*100
            excursion["mae"]=min(excursion["mae"],move);excursion["mfe"]=max(excursion["mfe"],move)
        for order in list(self.orders[user]):
            if order.instrument_id != quote.instrument_id or order.status not in {"accepted", "partially_filled"}:
                continue
            hit = (
                order.order_type == "limit" and ((order.side == "buy" and quote.price <= order.limit_price) or
                                                   (order.side == "sell" and quote.price >= order.limit_price))
            ) or (
                order.order_type in {"stop", "stop_limit"} and
                ((order.side == "buy" and quote.price >= order.stop_price) or
                 (order.side == "sell" and quote.price <= order.stop_price))
            )
            if not hit:
                continue
            remaining = order.quantity - order.filled_quantity
            fill_quantity = min(remaining, available_quantity) if available_quantity is not None else remaining
            if fill_quantity <= 0 or not self._execute(user, order, quote, fill_quantity):
                continue
            changed.append(order)
            if order.status == "filled" and order.oco_group:
                for sibling in self.orders[user]:
                    if sibling.id != order.id and sibling.oco_group == order.oco_group and sibling.status in {"accepted", "partially_filled"}:
                        sibling.status, sibling.updated_at = "cancelled", utcnow()
                        changed.append(sibling)
        return changed


paper_broker = PaperBroker()
