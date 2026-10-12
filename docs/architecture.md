# Quiz Forge v1.0: architecture (each requirement on the part that meets it)

```
library + blueprint -> generate -> validate + guards -> bank/pending -> qf review -> export
                       nightly: Batch     eval gate in CI                        approved only
                       regenerate: now    usage log -> qf report
```

| Part | Meets | How |
|---|---|---|
| library loader, blueprint reader | FR-1, FR-2 | `[library] path` and a blueprint file per course (new in v1.0) |
| generate | FR-3, FR-6 | the route in `config.toml`: Haiku 5.5, low effort |
| validate, quote check, guards | FR-4, NFR-6 | the schema, the word-for-word quote, input and output guards (8.3) |
| `qf review` | FR-5 | the only writer of `bank/approved/`, sealed (8.2) |
| export | FR-7 | new in v1.0, after their schema arrives |
| nightly Batch path | NFR-1, NFR-3, NFR-4 | half price; done by morning |
| realtime path | NFR-2 | regenerate one lesson; p95 from the eval gate |
| `inference_geo="us"` on every request | NFR-5 | needs a 4.6 or later model: our route is one |
| eval gate, usage log, report | NFR-7, NFR-4 | CI on every change; cost per feature |
| pinned model ids, deprecation check | NFR-8 | ids in `config.toml`, never inline |

Open, for the next lessons: where it runs (9.4) and how a model or prompt change ships (9.5).
