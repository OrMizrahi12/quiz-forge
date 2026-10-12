# Plan: CI on Workload Identity Federation

Today the eval gate in `evals.yml` reads `ANTHROPIC_API_KEY` from a repository secret. With federation, GitHub's
identity token is exchanged for a short-lived Anthropic token, and no key is stored anywhere.

1. An organization admin creates a service account, a GitHub issuer and a federation rule whose subject matches
   `repo:<owner>/quiz-forge:pull_request`. (Organization settings: not done in this course.)
2. The gate job asks GitHub for an identity token and names the rule:

   ```yaml
   permissions:
     id-token: write
     contents: read
   env:
     ANTHROPIC_FEDERATION_RULE_ID: fdrl_...
     ANTHROPIC_ORGANIZATION_ID: ...
     ANTHROPIC_SERVICE_ACCOUNT_ID: svac_...
     ANTHROPIC_IDENTITY_TOKEN_FILE: /tmp/gha-jwt
   ```

   plus the docs' step that writes GitHub's token to `$ANTHROPIC_IDENTITY_TOKEN_FILE`.
3. Check which credential wins: `ANTHROPIC_API_KEY` sits above federation, so while the secret is set, it still does.
4. Remove the `ANTHROPIC_API_KEY` secret, confirm federation is now used, then delete the key.
