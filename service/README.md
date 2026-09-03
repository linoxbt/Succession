# Succession service

A thin HTTP layer over the `succession` package, backing the marketplace UI.

```bash
pip install -e "../packages/succession[dev,service]"
uvicorn service.app:app --reload --port 8000
```

Then `POST /api/demo/reset` to seed the seller and post the listing.

Every route delegates to the library — none of them reimplements a rule. The
preview route in particular returns exactly what `build_preview` produces, so
there is no second, more talkative code path for the UI to leak through.
