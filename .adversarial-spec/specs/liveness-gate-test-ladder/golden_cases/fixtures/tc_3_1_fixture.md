# Service Spec: Geocoding Lookup Service

## System Component: GeolocationResolver
The application relies on `GeolocationResolver` to resolve IP addresses to latitude/longitude coordinates using a public database API.

### Current Implementation
In the test suite, we use a static JSON mock containing hardcoded coordinates for `8.8.8.8`.

```python
class MockGeolocationResolver:
    def resolve(self, ip_address):
        return {"ip": ip_address, "lat": 37.751, "lng": -97.822}
```

### Promotion Opportunity
The geocoding API provides a lightweight, unauthenticated health-check endpoint `/status` and a static sandbox IP `127.0.0.9` that returns a deterministic response. We should promote this mock to use a constructive liveness technique (a real lightweight verification request targeting the status endpoint or local container mock) to ensure our code is live and the mock does not drift from reality.
