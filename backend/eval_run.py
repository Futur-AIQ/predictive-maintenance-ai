from src.rag.vector_store import vector_store
vector_store.initialize()
from src.evaluation.rag_evaluator import run_evaluation
result = run_evaluation('./data/processed')
overall = (result['faithfulness'] + result['answer_relevancy'] + result['context_precision'] + result['context_recall']) / 4
print('=== RAG EVALUATION RESULTS (IMPROVED) ===')
print(f"Faithfulness:      {result['faithfulness']*100:.1f}%  (was 60%)")
print(f"Answer Relevancy:  {result['answer_relevancy']*100:.1f}%  (was 39%)")
print(f"Context Precision: {result['context_precision']*100:.1f}%  (was 14%)")
print(f"Context Recall:    {result['context_recall']*100:.1f}%  (was 41%)")
print(f"Overall:           {overall*100:.1f}%  (was 38%)")
print(f"Sample count:      {result['sample_count']}")
