import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

from loguru import logger


def _get_eval_llm():
    """Try OpenRouter → Anthropic → OpenAI, return first available LLM (or None)."""
    from src.config import settings

    if settings.openrouter_api_key and settings.openrouter_model:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model,
                temperature=0,
            )
        except Exception:
            pass

    if settings.anthropic_api_key:
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                api_key=settings.anthropic_api_key,
                model="claude-sonnet-4-5",
                temperature=0,
            )
        except Exception:
            pass

    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-4o-mini",
                temperature=0,
            )
        except Exception:
            pass

    return None


# Sample evaluation questions for the predictive maintenance domain
_EVAL_QUESTIONS = [
    {
        "question": "What are the vibration limits for a turbofan engine?",
        "ground_truth": "Normal: <0.5 in/s, Warning: 0.5-1.0 in/s, Critical: >1.0 in/s requiring immediate shutdown",
        "context_query": "vibration limits turbofan engine",
    },
    {
        "question": "What is fault code F006 and how should it be handled?",
        "ground_truth": "F006 is a bearing failure on the LP shaft, classified as CRITICAL severity, requiring immediate engine removal within 2 hours",
        "context_query": "F006 bearing failure LP shaft",
    },
    {
        "question": "What is the maintenance interval for turbofan blade inspection?",
        "ground_truth": "500-cycle check for visual inspection, 1000-cycle check for borescope all stages, 5000-cycle check for full overhaul",
        "context_query": "turbofan maintenance interval blade inspection cycles",
    },
    {
        "question": "What causes cavitation in centrifugal pumps?",
        "ground_truth": "Cavitation is caused by low NPSH (Net Positive Suction Head), high fluid temperature, or excessive flow rate, and can be remedied by increasing suction pressure, reducing pump speed, or checking for blockages",
        "context_query": "cavitation centrifugal pump causes remedies",
    },
    {
        "question": "What is the piston ring replacement interval for the reciprocating compressor?",
        "ground_truth": "Piston rings should be inspected every 8000 hours and replaced if ring gap exceeds 0.018 inches or blowby exceeds 5%",
        "context_query": "piston ring replacement interval compressor",
    },
]


def _retrieve_context(query: str, k: int = 5) -> list[str]:
    """Retrieve context documents for evaluation."""
    try:
        from src.rag.retriever import retriever
        docs = retriever.retrieve(query, "technical_docs", k=k)
        return [doc.page_content for doc in docs]
    except Exception as e:
        logger.warning(f"Failed to retrieve context for evaluation: {e}")
        return []


def _generate_answer(question: str, contexts: list[str]) -> str:
    """Generate answer using available LLM."""
    context_text = "\n\n".join(contexts[:5]) if contexts else "No context available."
    prompt = (
        f"You are a technical expert in industrial equipment maintenance. "
        f"Answer the question using ONLY the information in the context below. "
        f"Include all specific numerical values, thresholds, and time intervals from the context. "
        f"Do not add information not present in the context. Be concise and precise.\n\n"
        f"CONTEXT:\n{context_text}\n\n"
        f"QUESTION: {question}\n\n"
        f"ANSWER (cite specific values from the context):"
    )

    llm = _get_eval_llm()
    if llm is None:
        return "Unable to generate answer — no LLM available."

    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        return "Unable to generate answer — no LLM available."


def _compute_simple_metrics(
    questions: list[dict],
    answers: list[str],
    contexts: list[list[str]],
) -> dict:
    """
    Compute simplified RAG metrics without full RAGAS when it fails.
    Uses keyword overlap as a proxy for relevance metrics.
    """
    faithfulness_scores = []
    relevancy_scores = []
    precision_scores = []
    recall_scores = []

    for q, ans, ctx_list, gt in zip(
        [d["question"] for d in questions],
        answers,
        contexts,
        [d["ground_truth"] for d in questions],
    ):
        # Faithfulness: fraction of answer tokens present in context
        ans_tokens = set(ans.lower().split())
        ctx_text = " ".join(ctx_list).lower()
        ctx_tokens = set(ctx_text.split())
        if ans_tokens:
            faithfulness = len(ans_tokens & ctx_tokens) / len(ans_tokens)
        else:
            faithfulness = 0.0
        faithfulness_scores.append(min(faithfulness, 1.0))

        # Answer relevancy: overlap between answer and question keywords
        q_tokens = set(q.lower().split()) - {"the", "a", "an", "is", "what", "how", "for", "in"}
        if q_tokens:
            relevancy = len(set(ans.lower().split()) & q_tokens) / len(q_tokens)
        else:
            relevancy = 0.5
        relevancy_scores.append(min(relevancy, 1.0))

        # Context precision: for each retrieved chunk, what fraction of the ground
        # truth does it cover?  Averaging this across chunks measures whether the
        # retrieved chunks collectively contain the answer — without penalising
        # larger chunks that naturally contain more surrounding context.
        gt_tokens = set(gt.lower().split())
        if ctx_list and gt_tokens:
            prec_scores = []
            for c in ctx_list:
                c_tokens = set(c.lower().split())
                coverage = len(c_tokens & gt_tokens) / len(gt_tokens)
                prec_scores.append(min(coverage, 1.0))
            precision_scores.append(sum(prec_scores) / len(prec_scores))
        else:
            precision_scores.append(0.0)

        # Context recall: fraction of ground truth covered by context
        all_ctx_tokens = set(" ".join(ctx_list).lower().split())
        if gt_tokens:
            recall = len(gt_tokens & all_ctx_tokens) / len(gt_tokens)
        else:
            recall = 0.0
        recall_scores.append(min(recall, 1.0))

    def avg(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    return {
        "faithfulness": avg(faithfulness_scores),
        "answer_relevancy": avg(relevancy_scores),
        "context_precision": avg(precision_scores),
        "context_recall": avg(recall_scores),
    }


def run_evaluation(processed_data_dir: str = "./data/processed") -> dict:
    """
    Run RAGAS evaluation on the RAG pipeline.
    Falls back to simple keyword-overlap metrics if RAGAS is unavailable.
    """
    logger.info("Starting RAG evaluation...")
    os.makedirs(processed_data_dir, exist_ok=True)

    # Collect contexts and generate answers
    all_contexts = []
    all_answers = []

    for sample in _EVAL_QUESTIONS:
        contexts = _retrieve_context(sample["context_query"], k=5)
        answer = _generate_answer(sample["question"], contexts)
        all_contexts.append(contexts)
        all_answers.append(answer)
        logger.info(f"Evaluated: {sample['question'][:50]}...")

    # Try RAGAS first, fall back to simple metrics
    metrics = None
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        data = {
            "question": [s["question"] for s in _EVAL_QUESTIONS],
            "answer": all_answers,
            "contexts": all_contexts,
            "ground_truth": [s["ground_truth"] for s in _EVAL_QUESTIONS],
        }
        dataset = Dataset.from_dict(data)
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from ragas.run_config import RunConfig
        from src.config import settings

        judge_llm = _get_eval_llm()
        if judge_llm is None:
            raise RuntimeError("No LLM available to judge RAGAS metrics.")

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=judge_llm,
            embeddings=HuggingFaceEmbeddings(model_name=settings.embedding_model),
            run_config=RunConfig(max_workers=1, timeout=180),
        )
        def _nanmean(vals: list) -> float:
            """Mean of a list, ignoring None and NaN values."""
            valid = [v for v in vals if v is not None and v == v]
            return sum(valid) / len(valid) if valid else 0.0

        metrics = {
            "faithfulness": round(_nanmean(result["faithfulness"]), 4),
            "answer_relevancy": round(_nanmean(result["answer_relevancy"]), 4),
            "context_precision": round(_nanmean(result["context_precision"]), 4),
            "context_recall": round(_nanmean(result["context_recall"]), 4),
        }
        logger.info("RAGAS evaluation complete.")
    except Exception as e:
        logger.warning(f"RAGAS evaluation failed ({e}), using simple metrics.")
        metrics = _compute_simple_metrics(_EVAL_QUESTIONS, all_answers, all_contexts)

    report = {
        **metrics,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(_EVAL_QUESTIONS),
    }

    # Persist to disk
    report_path = os.path.join(processed_data_dir, "latest_evaluation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Evaluation report saved to {report_path}: {metrics}")
    return report


def load_latest_evaluation(processed_data_dir: str = "./data/processed") -> Optional[dict]:
    """Load the most recent evaluation report from disk."""
    report_path = os.path.join(processed_data_dir, "latest_evaluation.json")
    if not os.path.exists(report_path):
        return None
    with open(report_path) as f:
        return json.load(f)
