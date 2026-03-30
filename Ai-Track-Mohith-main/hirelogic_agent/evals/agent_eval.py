"""
HireLogic Agent Evaluation Suite
==================================
Evaluates the 5-agent HireLogic pipeline using
Google ADK AgentEvaluator with golden datasets.

Design philosophy:
- Each test has a documented purpose (WHY it exists)
- Logs are captured and preserved for every run
- Scores are printed as a markdown table
- Failures explain what went wrong and why it matters

Run:
  pytest evals/agent_eval.py -v -s

Requirements:
  - Backend running on localhost:8000
  - GEMINI_API_KEY in hirelogic_agent/.env
  - google-adk[eval] installed
"""

from __future__ import annotations

import importlib
import io
import json
import logging
import os
import re
import sys
import time
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_config import get_eval_metrics_from_config
from google.adk.evaluation.eval_result import EvalCaseResult
from google.adk.evaluation.eval_set import EvalSet
from google.adk.evaluation.simulation.user_simulator_provider import UserSimulatorProvider

AGENTS_DIR = Path(__file__).resolve().parents[1]
load_dotenv(AGENTS_DIR / ".env")
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

EVALS_DIR = Path(__file__).resolve().parent
DATA_DIR = EVALS_DIR / "data"
RUNS_DIR = EVALS_DIR / "runs"
RUNS_DIR.mkdir(exist_ok=True)

THRESHOLDS_RANKING = {
    "rubric_based_tool_use_quality_v1": 0.70,
    "hallucinations_v1": 0.50,
    "final_response_match_v2": 0.70,
}

THRESHOLDS_BIAS = {
    "rubric_based_tool_use_quality_v1": 0.60,
    "hallucinations_v1": 0.50,
    "final_response_match_v2": 0.60,
}

THRESHOLDS_FOLLOWUP = {
    "rubric_based_tool_use_quality_v1": 0.60,
    "final_response_match_v2": 0.60,
}

FAILURE_EXPLANATIONS = {
    "rubric_based_tool_use_quality_v1": (
        "The judge found weak tool usage quality. This usually means arguments "
        "were not grounded in the available context, candidate IDs did not line "
        "up cleanly, or fairness constraints were not followed consistently."
    ),
    "final_response_match_v2": (
        "The final ranking response was not semantically close enough to the "
        "golden answer. This matters because recruiters must receive the correct "
        "top candidate and a coherent shortlist explanation."
    ),
}


def setup_run_logger(test_name: str) -> tuple[logging.Logger, Path]:
    """
    Creates a logger that writes to both console
    AND a timestamped log file in evals/runs/.
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = RUNS_DIR / f"{ts}_{test_name}.log"

    logger = logging.getLogger(f"hirelogic_eval.{test_name}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    for adk_logger_name in [
        "google.adk",
        "google.adk.evaluation",
        "google.adk.runners",
        "google.adk.flows",
    ]:
        adk_logger = logging.getLogger(adk_logger_name)
        adk_logger.setLevel(logging.DEBUG)
        adk_logger.addHandler(file_handler)

    return logger, log_path


def print_score_table(
    test_name: str,
    scores: dict[str, float | None],
    thresholds: dict[str, float],
    elapsed: float,
    log_path: Path,
) -> bool:
    """Prints a markdown table of eval results."""
    print(f"\n{'=' * 60}")
    print(f"## HireLogic Eval — {test_name}")
    print(f"{'=' * 60}")
    print(
        f"| {'Metric':<38} | {'Score':>5} | {'Threshold':>9} | {'Status':<8} |"
    )
    print(f"|{'-' * 40}|{'-' * 7}|{'-' * 11}|{'-' * 10}|")

    all_pass = True
    for metric, threshold in thresholds.items():
        score = scores.get(metric)

        if score is None:
            status = "⚠️ N/A"
            all_pass = False
        elif score >= threshold:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_pass = False
        score_str = f"{score:.2f}" if score is not None else "N/A"
        print(
            f"| {metric:<38} | {score_str:>5} | {threshold:>9.2f} | "
            f"{status:<8} |"
        )

    print(f"\nRun time:  {elapsed:.1f}s")
    print(f"Log saved: {log_path.relative_to(AGENTS_DIR)}")
    print(f"Overall:   {'✅ ALL PASS' if all_pass else '⚠️  INCOMPLETE/FAIL'}")
    print(f"{'=' * 60}\n")
    return all_pass


def save_run_summary(
    test_name: str,
    scores: dict[str, float | None],
    thresholds: dict[str, float],
    elapsed: float,
    eval_cases: list[Any],
) -> Path:
    """Saves a JSON summary of the run to evals/runs/."""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    summary_path = RUNS_DIR / f"{ts}_{test_name}_summary.json"

    summary = {
        "test_name": test_name,
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "scores": scores,
        "thresholds": thresholds,
        "passed": all(
            scores.get(metric) is not None and scores.get(metric, 0.0) >= threshold
            for metric, threshold in thresholds.items()
        ),
        "eval_cases_run": len(eval_cases),
        "agent": "hirelogic_agent",
        "model": "gemini-2.5-flash",
    }

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return summary_path


def _import_agent_module(module_name: str):
    if str(AGENTS_DIR) not in sys.path:
        sys.path.insert(0, str(AGENTS_DIR))
    return importlib.import_module(module_name)


def _normalize_eval_set_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Accepts the friendlier `expected_tool_use` evalset shape requested for this
    project and converts it to the `intermediate_data.tool_uses` structure that
    the current ADK EvalSet schema accepts.
    """
    for eval_case in payload.get("eval_cases", []):
        for invocation in eval_case.get("conversation", []):
            expected_tool_use = invocation.pop("expected_tool_use", None)
            if expected_tool_use is None:
                continue

            intermediate_data = invocation.setdefault("intermediate_data", {})
            tool_uses = []
            for index, tool in enumerate(expected_tool_use, start=1):
                tool_uses.append(
                    {
                        "id": f"tool-{index:02d}",
                        "name": tool["tool_name"],
                        "args": tool.get("tool_input", {}),
                    }
                )
            intermediate_data["tool_uses"] = tool_uses
    return payload


def _load_eval_set(eval_file: Path) -> EvalSet:
    payload = json.loads(eval_file.read_text(encoding="utf-8"))
    normalized = _normalize_eval_set_payload(payload)
    return EvalSet.model_validate(normalized)


def _load_eval_config(config_file: Path) -> EvalConfig:
    return EvalConfig.model_validate_json(config_file.read_text(encoding="utf-8"))


def _apply_threshold_overrides(
    eval_config: EvalConfig, thresholds: dict[str, float]
) -> EvalConfig:
    for metric, threshold in thresholds.items():
        criterion = eval_config.criteria.get(metric)
        if criterion is not None:
            criterion.threshold = threshold
    return eval_config


def _extract_scores(output_text: str) -> dict[str, float]:
    """
    Parses numeric metric scores from ADK output. The evaluator prints explicit
    values on failures; on fully passing runs it may print no numeric scores.
    """
    scores: dict[str, float] = {}
    pattern = re.compile(
        r"Metric:\s*`(?P<metric>[^`]+)`\.\s*Expected threshold:\s*`[^`]+`,\s*"
        r"actual value:\s*`(?P<score>[-+]?\d*\.?\d+)`"
    )
    for match in pattern.finditer(output_text):
        scores[match.group("metric")] = float(match.group("score"))

    failure_pattern = re.compile(
        r"(?P<metric>[a-zA-Z0-9_]+)\s+for\s+None\s+Failed\.\s+Expected\s+"
        r"(?P<threshold>[-+]?\d*\.?\d+),\s+but\s+got\s+"
        r"(?P<score>[-+]?\d*\.?\d+)"
    )
    for match in failure_pattern.finditer(output_text):
        scores[match.group("metric")] = float(match.group("score"))

    return scores


def _extract_scores_from_text(output_text: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    patterns = [
        r"(rubric_based_tool_use_quality_v1)\s*[:\-]\s*([0-9.]+)",
        r"(final_response_match_v2)\s*[:\-]\s*([0-9.]+)",
        r"(tool_trajectory_avg_score)\s*[:\-]\s*([0-9.]+)",
        r"(response_match_score)\s*[:\-]\s*([0-9.]+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, output_text, re.IGNORECASE)
        for name, value in matches:
            try:
                scores[name] = float(value)
            except ValueError:
                continue
    return scores


def _extract_scores_from_eval_results(
    eval_results_by_eval_id: dict[str, list[EvalCaseResult]],
) -> dict[str, float]:
    aggregated: dict[str, list[float]] = {}

    for eval_results_per_eval_id in eval_results_by_eval_id.values():
        for eval_case_result in eval_results_per_eval_id:
            for metric_result in eval_case_result.overall_eval_metric_results:
                metric_name = getattr(metric_result, "metric_name", None)
                score = getattr(metric_result, "score", None)
                if metric_name and score is not None:
                    aggregated.setdefault(metric_name, []).append(float(score))

    return {
        metric_name: sum(values) / len(values)
        for metric_name, values in aggregated.items()
        if values
    }


async def _run_eval(
    test_name: str,
    eval_filename: str,
    purpose: str,
    thresholds: dict[str, float],
) -> None:
    logger, log_path = setup_run_logger(test_name)
    module_name = "agents.hirelogic_agent"
    _import_agent_module(module_name)

    eval_file = DATA_DIR / eval_filename
    config_file = EVALS_DIR / "test_config.json"

    assert eval_file.is_file(), (
        f"Golden dataset missing: {eval_file}\nRun from hirelogic_agent/ directory."
    )
    assert config_file.is_file(), f"Config missing: {config_file}"

    eval_set = _load_eval_set(eval_file)
    eval_config = _load_eval_config(config_file)
    eval_config = _apply_threshold_overrides(eval_config, thresholds)

    logger.info("=" * 50)
    logger.info("TEST: %s", test_name)
    logger.info("WHY: %s", purpose)
    logger.info("Loaded %s eval case(s) from %s", len(eval_set.eval_cases), eval_file.name)
    logger.info("=" * 50)

    start = time.time()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    eval_failure: AssertionError | None = None
    adk_return_value: Any = None
    eval_results_by_eval_id: dict[str, list[EvalCaseResult]] = {}

    agent_for_eval = await AgentEvaluator._get_agent_for_eval(
        module_name=module_name,
        agent_name=None,
    )
    eval_metrics = get_eval_metrics_from_config(eval_config)
    user_simulator_provider = UserSimulatorProvider(
        user_simulator_config=eval_config.user_simulator_config
    )

    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            eval_results_by_eval_id = await AgentEvaluator._get_eval_results_by_eval_id(
                agent_for_eval=agent_for_eval,
                eval_set=eval_set,
                eval_metrics=eval_metrics,
                num_runs=1,
                user_simulator_provider=user_simulator_provider,
            )

            failures: list[str] = []
            for _, eval_results_per_eval_id in eval_results_by_eval_id.items():
                eval_metric_results = (
                    AgentEvaluator._get_eval_metric_results_with_invocation(
                        eval_results_per_eval_id
                    )
                )
                failures.extend(
                    AgentEvaluator._process_metrics_and_get_failures(
                        eval_metric_results=eval_metric_results,
                        print_detailed_results=True,
                        agent_module=None,
                    )
                )

            failure_message = "Following are all the test failures.\n" + "\n".join(
                failures
            )
            assert not failures, failure_message
        except AssertionError as exc:
            eval_failure = exc

    elapsed = time.time() - start
    captured_output = stdout_buffer.getvalue()
    captured_error = stderr_buffer.getvalue()
    combined_output = "\n".join(
        part for part in [captured_output, captured_error, str(eval_failure or "")] if part
    )

    logger.info("ADK return type: %s", type(adk_return_value).__name__)
    logger.info(
        "ADK result has eval_case_results: %s",
        hasattr(adk_return_value, "eval_case_results"),
    )
    logger.info(
        "ADK result has eval_metric_results: %s",
        hasattr(adk_return_value, "eval_metric_results"),
    )

    if captured_output.strip():
        logger.info("Captured ADK stdout:\n%s", captured_output.rstrip())
    if captured_error.strip():
        logger.warning("Captured ADK stderr:\n%s", captured_error.rstrip())
    if eval_failure is not None:
        logger.error("Evaluator reported failure:\n%s", str(eval_failure).rstrip())

    scores: dict[str, float | None] = {metric: None for metric in thresholds}
    direct_scores = _extract_scores_from_eval_results(eval_results_by_eval_id)
    logger.info("scores extracted from return value: %s", direct_scores)
    scores.update(direct_scores)

    stdout_scores = _extract_scores(combined_output)
    if not stdout_scores:
        stdout_scores = _extract_scores_from_text(combined_output)
    logger.info("scores extracted from stdout: %s", stdout_scores)
    for metric, score in stdout_scores.items():
        scores.setdefault(metric, score)
        if scores.get(metric) is None:
            scores[metric] = score

    summary_path = save_run_summary(
        test_name=test_name,
        scores=scores,
        thresholds=thresholds,
        elapsed=elapsed,
        eval_cases=eval_set.eval_cases,
    )
    logger.info("Summary saved: %s", summary_path.name)

    print_score_table(test_name, scores, thresholds, elapsed, log_path)

    if eval_failure is None:
        for metric, threshold in thresholds.items():
            score = scores.get(metric)
            assert score is not None, (
                f"\n\n⚠️  METRIC NOT REPORTED: {metric}\n"
                f"ADK did not emit a numeric score for this metric.\n"
                f"This may mean:\n"
                f"  - The metric name in test_config.json does not match ADK's metric registry\n"
                f"  - The judge model did not respond\n"
                f"  - _extract_scores() failed to parse the output\n\n"
                f"Fix: check evals/runs/ log for this run and verify metric name spelling.\n"
                f"Full log: {log_path}\n"
            )
            assert score >= threshold, (
                f"\n\n❌ EVAL FAILURE: {metric}\n"
                f"   Score:     {score:.3f}\n"
                f"   Threshold: {threshold:.3f}\n"
                f"   Gap:       {threshold - score:.3f}\n"
                f"Full log: {log_path}\n"
            )
        return

    for metric, threshold in thresholds.items():
        score = scores.get(metric)
        assert score is not None, (
            f"\n\n⚠️  METRIC NOT REPORTED: {metric}\n"
            f"ADK did not emit a numeric score for this metric.\n"
            f"This may mean:\n"
            f"  - The metric name in test_config.json does not match ADK's metric registry\n"
            f"  - The judge model did not respond\n"
            f"  - _extract_scores() failed to parse the output\n\n"
            f"Fix: check evals/runs/ log for this run and verify metric name spelling.\n"
            f"Full log: {log_path}\n"
        )
        if score >= threshold:
            continue
        raise AssertionError(
            f"\n\n❌ EVAL FAILURE: {metric}\n"
            f"   Score:     {score:.3f}\n"
            f"   Threshold: {threshold:.3f}\n"
            f"   Gap:       {threshold - score:.3f}\n"
            f"Full log: {log_path}\n"
        ) from eval_failure

    raise AssertionError(
        "\n\n❌ EVAL FAILURE: AgentEvaluator reported a failure but no numeric "
        "metric scores could be extracted from the output.\n\n"
        f"Full logs: {log_path}\n"
        f"Summary:   {summary_path}\n"
    ) from eval_failure


@pytest.mark.asyncio
async def test_ranking_pipeline():
    """
    Full 5-agent ranking pipeline evaluation.

    WHY THIS EVAL EXISTS:
    The ranking pipeline is the core feature of
    HireLogic. This test validates the complete
    tool call sequence for a 3-candidate ranking.
    """
    await _run_eval(
        test_name="ranking_pipeline",
        eval_filename="evalset1.evalset.json",
        purpose=(
            "Validate the full ranking pipeline: job context, candidate fetch, "
            "resume analysis, scoring, bias detection, and final response."
        ),
        thresholds=THRESHOLDS_RANKING,
    )


@pytest.mark.asyncio
async def test_bias_detection():
    """
    Bias detection agent evaluation.

    WHY THIS EVAL EXISTS:
    HireLogic's fairness guarantee depends on the
    bias_agent correctly identifying anomalies.
    """
    await _run_eval(
        test_name="bias_detection",
        eval_filename="evalset2.evalset.json",
        purpose=(
            "Verify that bias detection is triggered correctly and the response "
            "remains fairness-first for recruiter-facing analysis."
        ),
        thresholds=THRESHOLDS_BIAS,
    )
