import json
import os
import random
from dataset_loader import load_and_merge_data
from baselines import BaselineA, BaselineB
from rag_system_sim import DualModalRAG
from evaluate import Evaluator

def main():
    print("--- 1. Loading Data ---")
    data = load_and_merge_data()
    
    # Debug: Check if data loaded
    if not data:
        print("No data found. Checking separate counts...")
        # We can re-run pieces of loader logic here or rely on loader's print
        print("Exiting.")
        return

    # Split Data (Simple 80/20 or Leave-One-Out)
    # Since we have ~50 items, let's just pick 10 random items as 'Test', rest as 'KB'
    random.seed(42)
    random.shuffle(data)
    test_size = 10
    if len(data) < test_size:
        test_size = len(data) // 2
        
    test_set = data[:test_size]
    kb_set = data[test_size:]
    
    print(f"Split: {len(test_set)} Test, {len(kb_set)} KnowledgeBase")

    print("\n--- 2. Initializing Models ---")
    baseline_a = BaselineA()
    baseline_b = BaselineB(kb_set) # Text RAG
    rag_ours = DualModalRAG(kb_set) # Dual Modal
    
    evaluator = Evaluator()
    
    results = []

    print("\n--- 3. Running Evaluation ---")
    for i, item in enumerate(test_set):
        song_name = item['SongName']
        print(f"[{i+1}/{len(test_set)}] Processing: {song_name}")
        
        gt_params = item['Parameters']
        
        # Prepare Inputs
        # Text Prompt: combined Style + Feature
        style_list = item.get('Style', [])
        feature_list = item.get('Feature', [])
        # Ensure lists
        if isinstance(style_list, str): style_list = [style_list]
        if isinstance(feature_list, str): feature_list = [feature_list]
        
        prompt_text = " ".join(style_list + feature_list)
        
        # Audio Vector (for Ours): item['Vector']
        audio_vec = item['Vector']
        if isinstance(audio_vec, str):
             audio_vec = [float(x) for x in audio_vec.split(',')]

        # 1. Baseline A (Zero-shot Sim)
        pred_a = baseline_a.generate(prompt_text, training_data=kb_set)
        
        # 2. Baseline B (Text RAG)
        pred_b = baseline_b.retrieve(prompt_text)
        
        # 3. Audio-Agent (Ours) - Dual Modal
        # Weight alpha=0.5
        pred_ours = rag_ours.retrieve(prompt_text, query_audio_vector=audio_vec, alpha=0.5)

        # Compute Metrics
        d_a = evaluator.compute_parameter_distance(pred_a, gt_params)
        d_b = evaluator.compute_parameter_distance(pred_b, gt_params)
        d_ours = evaluator.compute_parameter_distance(pred_ours, gt_params)

        results.append({
            "SongName": song_name,
            "BaselineA_Dist": d_a,
            "BaselineB_Dist": d_b,
            "Ours_Dist": d_ours
        })

    # Summary
    print("\n--- 4. Results Summary ---")
    if results:
        avg_a = sum(r['BaselineA_Dist'] for r in results) / len(results)
        avg_b = sum(r['BaselineB_Dist'] for r in results) / len(results)
        avg_ours = sum(r['Ours_Dist'] for r in results) / len(results)
        
        print(f"Average Parameter Distance (Lower is Better):")
        print(f"Baseline A (Random/Zero-shot): {avg_a:.4f}")
        print(f"Baseline B (Text RAG):         {avg_b:.4f}")
        print(f"Audio-Agent (Dual-Modal):      {avg_ours:.4f}")
        
        if avg_ours < avg_b:
            print("\nSUCCESS: Audio-Agent outperformed Text-Only RAG!")
        else:
            print("\nNote: Audio-Agent performance similar or worse than B. (Expected with simulated/perfect data)")
    else:
        print("No results generated.")

    # Save details
    with open(os.path.join(os.path.dirname(__file__), 'results.json'), 'w') as f:
        json.dump(results, f, indent=2)
    print("Detailed results saved to results.json")

if __name__ == "__main__":
    main()
