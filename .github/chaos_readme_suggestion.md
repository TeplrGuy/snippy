# Chaos Engineering & Load Testing - README Addition

## Try Locally

To test chaos engineering locally:

1. **Configure chaos settings** in `src/local.settings.json` (do not commit this file):
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "CHAOS_ENABLED": "true",
       "CHAOS_INJECT_ERROR_RATE": "0.25",
       "CHAOS_DELAY_SECONDS_MAX": "4",
       // ... other function settings
     }
   }
   ```

2. **Start the Functions host:**
   ```bash
   cd src
   func host start
   ```

3. **Test with HTTP requests** using your existing `.http` files or curl:
   ```bash
   curl -X POST http://localhost:7071/api/your-function-endpoint \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

4. **Observe chaos events** in the console logs:
   - Look for `CHAOS[error]` or `CHAOS[delay]` log entries
   - Error events will return HTTP 500 responses
   - Delay events will show increased response times

5. **Disable chaos** by setting `CHAOS_ENABLED=false` to compare baseline behavior.

## Recommended README Addition

Add this section to your project README:

---

### Chaos & Resilience Testing

This project includes automated chaos engineering to validate system resilience under failure conditions.

**Chaos Controls:**
- `CHAOS_ENABLED`: Master switch (default: false)
- `CHAOS_INJECT_ERROR_RATE`: Probability of service failures (0.0-1.0, default: 0.1)
- `CHAOS_DELAY_SECONDS_MAX`: Maximum random delay injection (default: 5 seconds)

**Automated Pipeline:**
Run the `Chaos and Performance Validation` workflow on feature branches (`feat/chaos-engineering`) to:
1. Deploy to isolated environment
2. Execute baseline load test (chaos disabled)
3. Execute chaos load test (chaos enabled)
4. Compare results against failure criteria
5. Report regression analysis

**Required Repository Secrets:**
- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- `LOAD_TEST_RESOURCE_NAME`, `LOAD_TEST_RESOURCE_GROUP`

**Monitoring:**
- Application Insights queries for chaos events: `traces | where message startswith "CHAOS["`
- Performance regression alerts when chaos degrades baseline > 60%
- Error rate thresholds to prevent excessive failure injection

The chaos system injects failures at I/O boundaries (Cosmos DB, vector search) to simulate real-world service degradation and validate error handling, timeouts, and recovery mechanisms.

---