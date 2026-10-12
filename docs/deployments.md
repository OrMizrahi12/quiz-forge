# Deployments: one install, separate data and identity

Each deployment is a folder made by `qf init`, chosen with `QF_HOME`. Nothing crosses from one to another.

| Boundary | How it holds | Checked by |
|---|---|---|
| Library | a copy inside the deployment; lesson ids come from its own `MANIFEST.json` | `test_a_lesson_outside_the_library_is_refused` |
| Settings, prompts, bank, logs | all under `QF_HOME` | `test_a_deployment_reads_its_own_settings_library_bank_and_log` |
| The library server | started with `QF_HOME` set; it gets no API key | `test_the_library_server_is_told_which_deployment_it_serves` |
| Identity | the deployment's own `.env` | see below |
| Coordination | `quizforge.fleet` reads each `runs/status.json`: numbers and ids, no content | `test_the_fleet_view_holds_numbers_and_ids_only` |

## Identity, for real use

| Deployment | Workspace | Credential | Spend limit |
|---|---|---|---|
| quiz-forge (our course) | its own workspace | a service account key, or WIF in CI (8.5) | the workspace limit |
| bakery | a second workspace | its own service account key | its own limit |

In this course both deployments use the one backstage key, in one workspace. A real second team gets its own
workspace, key and limit, so its usage, logs and spend are separate in the Console too.
