# Elice credentials and $10 campaign scope

User authorized the same frozen16dev inputs for6models, total budgetUSD10, in this chat2026-11-11. DEVON remains read-only. This scope approval does not certify live provider pricing, transport compatibility or human-reviewed labels.

Enter credentials only in `C:\Users\dreac\Desktop\kdt\model-lab\.env`. The runner reads this localfile and does not interpolate environment variables. The API key is supplied by Elice Serverless; `OPENAI_API_KEY` is the existing compatibility variable name. Use the model API example's exact `base_url` including `/v1`; the runner appends `/responses`.

For one common endpoint/key fill `OPENAI_API_KEY` and `LLM_BASE_URL`. For model-specific endpoints fill corresponding `MODEL_<MODEL>_BASE_URL`; a blank model-specific key uses the common key. A nonempty `MODEL_<MODEL>_API_KEY` overrides the common key. Missing resolved endpoint or key blocks execution. Model IDs are read from the already-created manifests, not `LLM_DEFAULT_MODEL`.

The total budget is recorded in `campaigns/dev-30pct-10usd.json`. Its18 planned allocations sum to10, with192 totalHTTPattempts including original retries. Each model cap is divided among A/Bmain/Blegacy in22/32,8/32,2/32 proportions. These allocations are deliberately not10 dollars per plan. No repeat or extra paid Judge/smoke is authorized by this configuration.

No APIcall occurs from creating these templates. The campaign remains pendingcredentials and implementation/preflight verification for aggregate enforcement and supplied cache-write/usage billing. Current single-plan execution is not evidence that a global campaign ledger exists. Do not start18independentplans with10dollars each. Any missing or unknown usage must stop the whole campaign. Exactcache tariffs from the attachment are partly inconsistent, so active pricing is not guessed or changed here.

After credentials are filled, finalize model-specific endpoint-pinned plans and enforce aggregate budget before any network call. Record all actual attempts/failures/retries and preserve all labels asunreviewed. This setup task itself creates no real execution approval file and makes no APIrequest.
