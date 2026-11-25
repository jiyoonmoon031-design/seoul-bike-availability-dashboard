# EC2 rollback runbook

1. Remove public access or place the service in maintenance mode if data or
   secret exposure is suspected.
2. Stop the new Backend and AI units without deleting the release directory.
3. Restore `/opt/seoul-bike/current` to the recorded previous release symlink.
4. Restore the previous root-owned environment files.
5. If a schema migration occurred, restore the verified MySQL backup according
   to the approved database procedure; do not run an unreviewed reverse DDL.
6. Start AI, Backend and Nginx, then run health checks and a minimal external
   HTTPS E2E.
7. Verify that ports 3306/8000/8080 remain private and review logs for secrets.
8. Record the failed commit, timestamps, symptoms, rollback checkpoint and data
   restoration result. Preserve the failed release for investigation.

Rollback is complete only when the previous release passes health/E2E and the
database consistency check. EBS/MySQL backups are not deleted during rollback.
