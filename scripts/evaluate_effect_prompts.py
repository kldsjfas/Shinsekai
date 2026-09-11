"""Compare effect prompts on synthetic cases; never sends user chat history.

Run the same cases with the configured OpenAI-compatible model and the
captured PR #345 baseline. Reports contain model output and scores, never API keys.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.llm.template.dialog.context import DialogTemplateContext
from ai.llm.template.dialog.sections.dialog_template import DialogTemplateSection
from i18n import tr_in_bundle


CASES = {
    "zh_CN": {
        "labels": ["笔记本, 笔记", "雨声"],
        "inputs": [
            ("pickup", "（拿起笔记本，翻开第一页）", "image"),
            ("negated", "我没有拿起笔记本，请不要让它出现。", "none"),
            (
                "hypothetical",
                "如果明天拿起笔记本，会有什么感觉？现在先不碰它。",
                "none",
            ),
            ("unrelated_action", "我拿起杯子，笔记本还锁在柜子里。", "none"),
            ("memory", "我回忆昨天翻开笔记本的情景，今天它不在这里。", "none"),
            ("rain_start", "窗外开始下雨，雨声清晰可闻，并持续着。", "loop"),
            ("rain_stop", "刚才的雨停了，现在已经听不到雨声。", "stop"),
            ("unlisted", "（拿起一把银钥匙）", "none"),
        ],
    },
    "en": {
        "labels": ["notebook, journal", "rain"],
        "inputs": [
            ("pickup", "(I pick up the notebook and open its first page.)", "image"),
            (
                "negated",
                "I did not pick up the notebook. Do not make it appear.",
                "none",
            ),
            (
                "hypothetical",
                "How would picking up the notebook tomorrow feel? Leave it alone for now.",
                "none",
            ),
            (
                "unrelated_action",
                "I pick up a cup; the notebook is still locked in the cabinet.",
                "none",
            ),
            (
                "memory",
                "I remember opening the notebook yesterday. It is not here today.",
                "none",
            ),
            (
                "rain_start",
                "Rain starts outside. We can clearly hear it, and it continues.",
                "loop",
            ),
            ("rain_stop", "The rain has stopped. We can no longer hear it.", "stop"),
            ("unlisted", "(I pick up a silver key.)", "none"),
        ],
    },
    "ja": {
        "labels": ["ノート, 手帳", "雨音"],
        "inputs": [
            ("pickup", "（ノートを手に取り、最初のページを開く）", "image"),
            ("negated", "ノートは手に取っていません。出現させないでください。", "none"),
            (
                "hypothetical",
                "明日ノートを手に取ったらどう感じるだろう？今は触らない。",
                "none",
            ),
            (
                "unrelated_action",
                "カップを手に取る。ノートはまだ戸棚の中に施錠されている。",
                "none",
            ),
            ("memory", "昨日ノートを開いたことを思い出す。今日はここにない。", "none"),
            (
                "rain_start",
                "外で雨が降り始め、雨音がはっきり聞こえ続けている。",
                "loop",
            ),
            ("rain_stop", "先ほどの雨はやんだ。もう雨音は聞こえない。", "stop"),
            ("unlisted", "（銀の鍵を手に取る）", "none"),
        ],
    },
}


def context_for(language: str) -> DialogTemplateContext:
    return DialogTemplateContext(
        characters=(
            (
                "Alice",
                SimpleNamespace(
                    sprites=[object()],
                    emotion_tags="neutral: 01",
                    character_setting="A careful observer who responds to the player's actions without inventing new events.",
                ),
            ),
        ),
        translate=lambda key, **values: tr_in_bundle(
            f"template_gen.{key}", language, **values
        ),
        target_voice_name="Japanese",
        json_reminder="",
        use_effect=True,
        use_choice=False,
        use_narration=True,
        use_stat=False,
        max_dialog_items=2,
    )


def render_current(language: str) -> str:
    context = context_for(language)
    labels = tuple(CASES[language]["labels"])
    from ai.llm.template.effects import EffectPromptContext, build_effect_prompt_section

    return build_effect_prompt_section().render(
        EffectPromptContext(
            system_template=DialogTemplateSection().render(context),
            labels=labels,
            translate=context.translate,
        )
    )


def score_output(content: str, language: str, expected: str) -> dict:
    try:
        payload = json.loads(content)
        dialogs = payload.get("dialog", [payload])
        valid = bool(dialogs) and all(
            isinstance(item, dict)
            and item.get("character_name")
            and "speech" in item
            and "sprite" in item
            for item in dialogs
        )
        effects = [
            str(item.get("effect") or "").strip()
            for item in dialogs
            if item.get("effect")
        ]
    except (ValueError, TypeError, AttributeError):
        return {"valid": False, "correct": False, "effects": []}
    image_label, rain_label = CASES[language]["labels"]
    image_aliases = {image_label, *image_label.split(", ")}
    if expected == "none":
        correct = not effects
    elif expected == "image":
        correct = (
            len(effects) == 1
            and effects[0].removeprefix("before:").removeprefix("after:")
            in image_aliases
        )
    else:
        correct = effects == [f"{expected}:{rain_label}"]
    return {
        "valid": bool(valid),
        "correct": bool(valid and correct),
        "effects": effects,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=ROOT / "test/fixtures/effects/pr345-prompts.json",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not all((args.baseline, args.config, args.output)):
        parser.error("--baseline, --config and --output are required for a live run")
    import yaml
    from openai import OpenAI

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    config = config.get("api_config", config)
    provider = config["llm_provider"]
    model = config["llm_model"][provider]
    client = OpenAI(
        api_key=config["llm_api_key"][provider],
        base_url=config["llm_base_url"],
        timeout=60,
        max_retries=0,
    )
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    prompts = {
        "pr345": baseline,
        "sections": {language: render_current(language) for language in CASES},
    }
    # Remove the repeated effect explanation in the JSON example only.
    prompts["short_example"] = {
        language: text.replace(
            context_for(language).translate("json_line_effect"),
            '        "effect": "",\n',
        )
        for language, text in prompts["sections"].items()
    }
    jobs = [
        (variant, language, case)
        for variant in prompts
        for language in CASES
        for case in CASES[language]["inputs"]
    ]

    def run(job):
        variant, language, (case_id, user_input, expected) = job
        messages = [{"role": "system", "content": prompts[variant][language]}]
        if expected == "stop":
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "dialog": [
                                {
                                    "character_name": "Alice",
                                    "sprite": "01",
                                    "speech": "...",
                                    "effect": "loop:" + CASES[language]["labels"][1],
                                }
                            ]
                        },
                        ensure_ascii=False,
                    ),
                }
            )
        messages.append({"role": "user", "content": user_input})
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=700,
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            content = response.choices[0].message.content or ""
            return {
                "variant": variant,
                "language": language,
                "case": case_id,
                "expected": expected,
                "response": content,
                **score_output(content, language, expected),
            }
        except Exception as error:
            # Do not serialize exception text: provider errors may contain URLs.
            return {
                "variant": variant,
                "language": language,
                "case": case_id,
                "error": type(error).__name__,
                "valid": False,
                "correct": False,
            }

    with ThreadPoolExecutor(max_workers=3) as executor:
        rows = list(executor.map(run, jobs))
    report = {
        "baseline_ref": "e46c0ee71f977f6a7071dfb891af58576c2da87e",
        "model": model,
        "temperature": 0,
        "repeats": 1,
        "cases_per_variant": 24,
        "prompt_chars": {
            variant: {language: len(text) for language, text in values.items()}
            for variant, values in prompts.items()
        },
        "results": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for variant in prompts:
        selected = [row for row in rows if row["variant"] == variant]
        print(
            variant,
            {
                "correct": sum(row["correct"] for row in selected),
                "valid": sum(row["valid"] for row in selected),
                "errors": sum("error" in row for row in selected),
                "total": len(selected),
            },
            flush=True,
        )


if __name__ == "__main__":
    main()
