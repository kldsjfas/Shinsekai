# PR #345 effect prompt ablation

Baseline: `e46c0ee71f977f6a7071dfb891af58576c2da87e`.
Run date: 2026-09-11. Model: the locally configured `deepseek-v4-flash`,
temperature 0, thinking disabled, maximum 700 output tokens, no request retries.
Only synthetic prompts were sent; no saved characters, conversations, images,
or other user content were used. Each variant used eight cases in each of
Chinese, English, and Japanese, with one completion per case per run.

## Decisions

- Remove frontend and backend matching of translated headings to delete or
  relocate prompt text. The application resolves selected labels and playback
  maps; `ai/llm/template/effects.py` renders the catalog using Section nodes, and
  `ai/llm/template/integrations/effects.py` supplies translations. New generated
  templates retain the effect schema and rules. Current labels are composed
  once at launch, so changing the selection does not rewrite the saved template.
- Restore the existing JSON field contract and plugin patch placement for both
  indexed and semantic media modes. PR #345 had disabled the indexed field
  contract and duplicated customized fields in semantic mode. This restoration
  is a compatibility requirement, not a claim that longer prompts are better.
- Remove the worker's Chinese action regex fallback. With the fixed input
  “我拿起杯子，笔记本还锁在柜子里。” and a model reply confirming the notebook
  remains locked away, the old fallback inserts a notebook image anyway.
  Equivalent English/Japanese actions do not receive the same fallback. The
  worker now forwards the model's chosen or omitted effect unchanged.
- Remove duplicate catalog-header guidance and the added instruction to split
  simultaneous audio/images into adjacent dialogue items. Preserve the original
  audio timing/start/stop semantics, extending them only for images and aliases.
  Do not replace the effect example's explanation with an empty string: both
  model runs regressed with that ablation.

## Paired prompt comparisons

Success requires valid JSON with dialogue fields and exactly the expected effect
selection. Negative cases must omit effects. The sustained-rain cases require
`loop:<label>` and `stop:<label>`, respectively. An ordinary rain label is scored
as a timing failure even though it could still play a sound once.

| Variant                                                               | Exploratory run | Final run | JSON/required fields, each run |
| --------------------------------------------------------------------- | --------------: | --------: | -----------------------------: |
| Original PR prompt, before worker fallback                            |           20/24 |     20/24 |                          24/24 |
| Preserve contracts and compose catalog through Sections               |           19/24 |     22/24 |                          24/24 |
| Same Section variant, only replace effect example with `"effect": ""` |           12/24 |     15/24 |                          24/24 |

The exploratory Section variant retained the PR's effect copy. The final variant
restores explicit loop-start/stop wording and removes the extra catalog-header
and dialogue-splitting guidance described above. The empty-example comparison
changes only that JSON example line within each run; it is the single-factor
ablation. Baseline-to-final is a combined refactor, not an isolated measurement
of Section structure or any individual sentence.

The final failures are a missed Chinese notebook effect and an English notebook
event with invented rain. Removing the regex means model omissions can still
lead to missing images; it avoids silently contradicting the model or triggering
unrelated images. These 24 cases are a small regression set, reused during
development, not a held-out benchmark or evidence of general model superiority.
Temperature 0 does not guarantee identical completions across provider runs.

Prompt characters (Chinese / English / Japanese) changed from
`1439 / 2611 / 1293` to `1831 / 3906 / 1879`. The final prompt is longer because
the original field contract was restored. The goal is removing unauthorized
rewriting and unsupported heuristics, not minimizing character count.

## Reproduce and inspect

The captured original prompts are in
`test/fixtures/effects/pr345-prompts.json`. Both runs' raw responses, scores,
prompt lengths, and five deterministic fallback controls are in
`docs/evaluations/pr345-effects-results.json`.

```sh
python scripts/evaluate_effect_prompts.py \
  --config /path/to/data/config/api.yaml \
  --output /path/to/effects-results.json
```

The evaluator reads credentials locally and does not include them or provider
URLs in its report. It makes 72 requests per invocation with at most three
in flight. Transport failures are recorded separately from effect errors.

Regression tests cover literal prompt preservation, independent Section
disabling, three catalog locales, plugin field contracts, and worker forwarding.
All 192 effect-disabled template combinations retain the exact main-branch
digests. Effect-enabled digests change only for the revised effect copy.
