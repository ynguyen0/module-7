# Order Processing Simulation

Run the simulation with Python 3.10 or newer. It uses only the standard library.

```sh
python3 order_sim.py
```

Each event carries an `order_id`, `version`, and `status`. The store tracks the last applied version and buffers later events by version until it can apply them in sequence. It issues increasing fencing tokens per order and checks the token on every delivery before updating the order or its buffer. The simulation runs sequentially in memory and represents delayed messages by changing their delivery order.

## Example run

- **Out-of-order delivery and duplicate.** The program receives v2, v1, and v2 again. It buffers v2, applies v1 and v2 in order, then ignores the repeated v2.
- **Missing event.** Only v2 arrives. The order stays at v0 with no status, and the log records that v2 is pending while the store waits for v1.
- **Stale worker.** Worker B claims token 2 and applies v2. Worker A tries to ship the order with token 1 and is rejected. The order stays at `PAID` until worker B delivers the same v3 event with token 2.

```text
=== Out-of-order delivery and duplicate ===
order-1 | worker A claimed token 1
order-1 | v2 PAID | buffered, waiting for v1
order-1 | v1 CREATED | applied
order-1 | v2 PAID | applied
order-1 | v2 PAID | duplicate ignored
order-1 | current v2 (PAID), pending []

=== Missing event ===
order-2 | worker A claimed token 1
order-2 | v2 PAID | buffered, waiting for v1
order-2 | current v0 (no status), pending [2]

=== Stale worker ===
order-3 | worker A claimed token 1
order-3 | v1 CREATED | applied
order-3 | worker B claimed token 2
order-3 | v2 PAID | applied
order-3 | v3 SHIPPED | rejected token 1, current token 2
order-3 | current v2 (PAID), pending []
order-3 | v3 SHIPPED | applied
order-3 | current v3 (SHIPPED), pending []
```

## Reflection

Different machines can disagree about the time, so a later update can receive an earlier wall-clock timestamp. Network delays and retries also mean messages can arrive out of order or more than once. Even with synchronized clocks, seeing an update's timestamp does not tell the receiver whether a preceding update is missing. Sequential versions reveal gaps and repeated updates, and fencing tokens let the store reject writes from workers whose authority has expired.
