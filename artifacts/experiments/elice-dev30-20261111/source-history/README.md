# Execution source provenance

The five archived run directories preserve the original plans and responses. This directory separately preserves 13 historical model-lab source files whose hashes differ from the published current source. The snapshots are byte-exact copies of the specific relevant backups. Unrelated integration outputs and backups are excluded.

[index.json](index.json) records each snapshot's original path relative to the old model-lab root, runtime source path, execution stage, SHA-256, byte count, exported path, and originating runs. Its five execution-stage records contain the complete captured model-lab source fingerprints and reconstruction references. There are 71 distinct source paths across the campaign: the initial, continuation-1 and recovery-2 plans each capture 70 files; recovery-3 and recovery-4 each capture 71.

To reconstruct one stage offline, start with a separate copy of the published repository's current source. For the chosen `execution_stages` record, retain every file marked `repository_root` and replace each file marked `source_history` with its indexed snapshot at the fingerprint `path`. Verify every captured file against its SHA-256 and byte count. This reconstructs the captured source set; it does not resume a campaign, authorize calls, recreate environment credentials, or guarantee identical provider responses.

Some snapshots apply to multiple origins. The `stage` directory identifies when that preserved version was needed; `captured_in_origins` and the complete stage maps identify all origins that used it. Original run files and their hashes remain unchanged.

The published root `elice_billing.py` includes the postrun top-level `cache_write_tokens` alias patch. All five executions used the snapshot at `snapshots/all-execution-stages/elice_billing.py` with SHA-256 `0936af3cb46aaf12ac966a9b41dc04e33bf82149a80ec911ae47039d7b626f6b`. The postrun source has SHA-256 `a83265ddda3a6ea155e320a278349007bd9acbe86d38c21ceef03985fd6aa5ac`. Recorded cost ranges, reservations and budget debits were preserved without retrospective repricing.

[devon-reference.json](devon-reference.json) pins the external DEVON checkout to commit `1bb0e33f30c95d578174208c3ee76192a4016b70`, records the identical 42 DEVON source fingerprints captured by all 90 plans, and records four captured prompt fingerprints. It includes references and hashes only; DEVON source content is not vendored. Use an authorized checkout of that commit and pass its location through `--devon-root` or `DEVON_ROOT`. Historical manifest template paths and evidence paths retain the original machine locations; regenerate working manifests for the new checkout.

Package versions are recorded separately in the repository's `requirements-offline.txt`. They came from Python 3.13.7 and are not a resolver-generated lockfile. Reconstruction supports an evidence audit; it does not establish bit-for-bit environment or model-response reproducibility.
