"""Simulate ordered event delivery and fenced order updates."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    order_id: str
    version: int
    status: str


@dataclass
class Order:
    version: int = 0
    status: str | None = None
    fencing_token: int = 0
    pending: dict[int, Event] = field(default_factory=dict)


class OrderStore:
    def __init__(self):
        self.orders: dict[str, Order] = {}

    def claim(self, order_id: str, worker: str) -> int:
        if order_id not in self.orders:
            self.orders[order_id] = Order()
        order = self.orders[order_id]
        order.fencing_token += 1
        print(f"{order_id} | {worker} claimed token {order.fencing_token}")
        return order.fencing_token

    def deliver(self, event: Event, token: int) -> None:
        order = self.orders[event.order_id]
        label = f"{event.order_id} | v{event.version} {event.status}"

        if token != order.fencing_token:
            print(f"{label} | rejected token {token}, current token {order.fencing_token}")
            return

        if event.version <= order.version or event.version in order.pending:
            print(f"{label} | duplicate ignored")
            return

        order.pending[event.version] = event
        next_version = order.version + 1
        if event.version > next_version:
            print(f"{label} | buffered, waiting for v{next_version}")
            return

        while order.version + 1 in order.pending:
            ready = order.pending.pop(order.version + 1)
            order.version = ready.version
            order.status = ready.status
            print(f"{ready.order_id} | v{ready.version} {ready.status} | applied")

    def show(self, order_id: str) -> None:
        order = self.orders[order_id]
        status = order.status or "no status"
        print(f"{order_id} | current v{order.version} ({status}), pending {sorted(order.pending)}")


def main() -> None:
    store = OrderStore()

    print("=== Out-of-order delivery and duplicate ===")
    token = store.claim("order-1", "worker A")
    paid = Event("order-1", 2, "PAID")
    store.deliver(paid, token)
    store.deliver(Event("order-1", 1, "CREATED"), token)
    store.deliver(paid, token)
    store.show("order-1")

    print("\n=== Missing event ===")
    token = store.claim("order-2", "worker A")
    store.deliver(Event("order-2", 2, "PAID"), token)
    store.show("order-2")

    print("\n=== Stale worker ===")
    old_token = store.claim("order-3", "worker A")
    store.deliver(Event("order-3", 1, "CREATED"), old_token)
    new_token = store.claim("order-3", "worker B")
    store.deliver(Event("order-3", 2, "PAID"), new_token)
    shipped = Event("order-3", 3, "SHIPPED")
    store.deliver(shipped, old_token)
    store.show("order-3")
    store.deliver(shipped, new_token)
    store.show("order-3")


if __name__ == "__main__":
    main()
