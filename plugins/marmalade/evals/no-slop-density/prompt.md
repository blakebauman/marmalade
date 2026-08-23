---
tags: no-slop, authoring
runs: 3
---
Here's our order pipeline. Draw me a Mermaid diagram of it.

Checkout service receives the cart, validates stock against the inventory
service, reserves it, writes an order row, publishes to an order queue. A
payments worker picks it up, calls Stripe, and on success publishes to a
fulfilment queue. A fulfilment worker reserves a courier slot, prints a label,
and marks the order shipped. On a Stripe decline the payments worker releases
the stock reservation and emails the customer. There's also a nightly reconciler
that walks unshipped orders older than 48h and re-queues them, an admin console
that can force-ship, a webhook receiver for Stripe async events, a fraud check
between validation and reservation, and a metrics sidecar on every service.
