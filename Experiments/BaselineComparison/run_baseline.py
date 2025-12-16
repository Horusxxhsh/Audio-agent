import json
import os
import random
import sys

# Add common directory to sys.path
common_dir = os.path.join(os.path.dirname(__file__), '..', 'common')
sys.path.append(common_dir)

from dataset_loader import load_and_merge_data
from baselines import GenerativeAgent, TextRetriever, DualModalRetriever
from evaluate import Evaluator

def main():
    print("--- 1. Loading Data ---")
    data = load_and_merge_data()
    if not data:
        print("No data found. Exiting.")
        return

    # Split Data
    random.seed(42)
    random.shuffle(data)
    test_size = 10
    if len(data) < test_size:
        test_size = len(data) // 2
        
    test_set = data[:test_size]
    kb_set = data[test_size:]
    
    print(f"Split: {len(test_set)} Test, {len(kb_set)} KnowledgeBase")

    print("\n--- 2. Initializing Generative Agent & Retrievers ---")
    agent = GenerativeAgent()
    text_retriever = TextRetriever(kb_set)
    dual_retriever = DualModalRetriever(kb_set)
    evaluator = Evaluator()
    
    results = []

    print("\n--- 3. Running Generative Evaluation (3 Modes) ---")
    for i, item in enumerate(test_set):
        song_name = item['SongName']
        print(f"[{i+1}/{len(test_set)}] Processing: {song_name}")
        
        gt_params = item['Parameters']
        
        # Prepare Inputs
        style_list = item.get('Style', [])
        feature_list = item.get('Feature', [])
        prompt_text = " ".join(style_list + feature_list) # simple string concat
        
        audio_vec = item.get('Vector') # Raw vector from DB (list of floats usually)
        # dataset_loader might return it as string or list, ensure list for retriever
        if isinstance(audio_vec, str):
             try:
                 audio_vec = [float(x) for x in audio_vec.split(',')]
             except:
                 audio_vec = []

        # Mode A: Zero-shot (Baseline A)
        print("   > Mode A: Zero-shot Generation...")
        pred_a = agent.generate(prompt_text, mode="zero_shot")

        # Mode B: Text RAG (Baseline B)
        print("   > Mode B: Text RAG Generation...")
        ctx_text = text_retriever.retrieve_top_k(prompt_text, k=3)
        pred_b = agent.generate(prompt_text, context_items=ctx_text, mode="rag")

        # Mode C: Dual RAG (Ours)
        print("   > Mode C: Dual RAG Generation (Ours)...")
        ctx_dual = dual_retriever.retrieve_top_k(prompt_text, query_audio_vector=audio_vec, alpha=0.5, k=3)
        pred_c = agent.generate(prompt_text, context_items=ctx_dual, mode="rag_cot")

        # Compute Metrics
        d_a = evaluator.compute_parameter_distance(pred_a, gt_params)
        d_b = evaluator.compute_parameter_distance(pred_b, gt_params)
        d_c = evaluator.compute_parameter_distance(pred_c, gt_params)

        results.append({
            "SongName": song_name,
            "BaselineA_ZeroShot_Dist": d_a,
            "BaselineB_TextRAG_Dist": d_b,
            "Ours_DualRAG_Dist": d_c
        })

    # Summary
    print("\n--- 4. Results Summary ---")
    if results:
        avg_a = sum(r['BaselineA_ZeroShot_Dist'] for r in results) / len(results)
        avg_b = sum(r['BaselineB_TextRAG_Dist'] for r in results) / len(results)
        avg_c = sum(r['Ours_DualRAG_Dist'] for r in results) / len(results)
        
        print(f"Average Parameter Distance (Lower is Better):")
        print(f"Baseline A (Zero-shot): {avg_a:.4f}")
        print(f"Baseline B (Text RAG):  {avg_b:.4f}")
        print(f"Ours (Dual RAG):        {avg_c:.4f}")
        
    else:
        print("No results generated.")

    # Save details
    with open(os.path.join(os.path.dirname(__file__), 'results.json'), 'w') as f:
        json.dump(results, f, indent=2)
    print("Detailed results saved to results.json")

if __name__ == "__main__":
    main()
