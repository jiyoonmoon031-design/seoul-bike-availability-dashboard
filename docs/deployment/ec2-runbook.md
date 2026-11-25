# EC2 deployment runbook

This runbook is a prepared procedure, not evidence that production was
deployed. Do not continue past the preflight gate without reviewer approval,
verified SSH access, a backup, a rollback checkpoint and a valid HTTPS domain.

## 1. Read-only preflight

Record the instance ID/type, OS release, CPU/RAM/disk, public domain/IP,
Security Group ingress, MySQL version/status, Java version, Python version,
current service layout and current release symlink. Confirm that only 22 from
the approved administration range and 80/443 from the intended audience are
allowed. Ports 3306, 8000 and 8080 must not be public.

Stop if any item is unknown. Never infer EC2 state from local configuration.

## 2. Backup and checkpoint

1. Create an encrypted MySQL backup and verify that it can be listed/read.
2. Record the current `/opt/seoul-bike/current` symlink target and Git commit.
3. Archive current environment files without printing their contents.
4. Record checksums of the deployed JAR, frontend assets, model, fallback and
   feature table.
5. Create an EBS snapshot or the team's approved equivalent.

## 3. Build release artifacts

Run the repository's full verification first. Build the frontend with
`npm run build` and the backend with `./gradlew bootJar`. Create a versioned
release directory under `/opt/seoul-bike/releases/<commit>` owned by the
`seoulbike` service account. Copy the tracked source/build outputs and the three
verified, untracked data/model artifacts separately.

Expected checksums:

- RF: `e8b7543db145c63259301e60cf6fe248843ec9327cfe85f0c2323cba432deadd`
- B3: `578d679fec113d0c112ed0c2181319939b2ce167ff665f2ad542d61c082f821e`
- feature table: `e1c94933347c27ef80bb4dc8a774960497ec6de94455cc195266aefd551e5202`

## 4. Secrets and services

Store environment files as root-owned mode `0600` files under
`/etc/seoul-bike`; never copy examples verbatim. Install the systemd units and
Nginx template after substituting the approved domain. Keep AI and Backend on
loopback. Enable LLM authentication and inject `X-LLM-Token` only at a trusted
authenticated gateway boundary; never ship the token in frontend JavaScript.

Run `systemd-analyze verify` and `nginx -t`, then start AI, Backend and Nginx in
that order. Use Certbot or the team's existing certificate process for HTTPS.

## 5. Health and E2E gate

Verify loopback AI health, Backend health/API, MySQL snapshot persistence,
external HTTPS, route search, prediction provenance, explicit route fallback,
operator rebalancing and all GPT actions. Restart each service once and verify
recovery. Confirm that ports 3306/8000/8080 are unreachable externally and scan
logs for secret values before opening access.

## 6. Release

Only after the reviewer/security gate succeeds, atomically update the `current`
symlink, reload systemd/Nginx and monitor errors/latency. If any health or E2E
gate fails, follow `rollback-runbook.md` immediately.
