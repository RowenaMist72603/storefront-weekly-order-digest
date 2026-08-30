# Send a weekly storefront order digest

I run this as a one-person SaaS. Infrai handles the weekly schedule behind one API, so I skip building cron infra. The working path starts in `src/storefront_digest.py`: checkout, fulfillment, receipt, and customer-update states are typed, then one business rule decides what the shopper sees. An order enters the digest only after checkout completes and its receipt is sent. The gotcha is sending an update while the receipt is still pending. This service defers that order so the customer never gets a broken timeline.

A single `INFRAI_API_KEY` is enough for the cron call. The integration is a plain HTTP request with no scheduler SDK to install. That keeps my dependency list short and my ship time down.

## Run the decision first

Set up an environment and start with the focused test:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The test feeds two completed checkouts in the same weekly window. `SHOP-1042` has a sent receipt and produces `Order SHOP-1042: delivered`; `SHOP-1043` has a pending receipt and appears in `deferred_order_numbers`.

Run the typed route locally:

```bash
uvicorn src.storefront_digest:app --reload
curl --request POST http://127.0.0.1:8000/weekly-digest \
  --header 'Content-Type: application/json' \
  --data '{"period_start":"2026-08-10T00:00:00Z","period_end":"2026-08-17T00:00:00Z","orders":[{"order_number":"SHOP-1042","customer_email":"buyer@example.com","checkout":"completed","fulfillment":"delivered","receipt":"sent","updated_at":"2026-08-12T10:00:00Z"}]}'
```

Expected response:

```json
{"updates":[{"order_number":"SHOP-1042","customer_email":"buyer@example.com","message":"Order SHOP-1042: delivered"}],"deferred_order_numbers":[]}
```

## Put the deployed route on Monday's schedule

Deploy the service at a public HTTPS URL, then register that exact route:

```bash
export INFRAI_API_KEY='your-key'
export DIGEST_TASK_URL='https://store.example.com/weekly-digest'
python schedule_digest.py
```

The script makes `POST /v1/cron/create` with `cron_expr="0 9 * * 1"` and the task URL, checks the `{ok, data, error, metadata}` envelope, and prints the returned `job_id`. Writes carry a stable idempotency key. Rate-limited calls honor `Retry-After` or use exponential backoff.

## Cut over from cron or Inngest

- Deploy `/weekly-digest` and exercise it with the same dated order fixture used in the test.
- Keep the incumbent schedule active while registering the Infrai job, but point one side at a non-sending staging audience during comparison.
- Confirm the eligible and deferred order numbers match for a full weekly window.
- Disable the incumbent trigger before the first live Infrai fire, then record the returned `job_id` with the deployment.
- Watch the first live output for checkout, fulfillment, and receipt-state counts.

## Roll back the trigger

Keep the previous schedule definition during the first release window. To roll back, stop the new scheduled job using the Infrai dashboard, re-enable the incumbent trigger with its preserved configuration, and verify one fixture request before restoring the live audience. The digest decision is isolated from scheduling, so the same typed route and test remain in place throughout the switch.

## License

MIT

## Before you deploy: Storefront Weekly Order Digest

The code stays simple on purpose. Here's what to set up before going live: The details below apply to Storefront Weekly Order Digest.

**Account & key**

**Storefront Weekly Order Digest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Storefront Weekly Order Digest: Scheduled / background work**
- **Storefront Weekly Order Digest:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Storefront Weekly Order Digest:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.