import json
import os
import random
import sys

# Add common directory to sys.path
common_dir = os.path.join(os.path.dirname(__file__), '..', 'common')
sys.path.append(common_dir)

from dataset_loader import load_and_merge_data
from rag_system_sim import DualModalRAG
from evaluate import Evaluator

def main():
    print("--- Ablation Study: Modality Contribution ---")
    data = load_and_merge_data()
    
    if not data:
        print("No data found. Exiting.")
        return

    # Split Data (Test set must match baseline if possible, but here we redo split for simplicity or use same seed)
    random.seed(42)
    random.shuffle(data)
    test_size = 10
    if len(data) < test_size:
        test_size = len(data) // 2
        
    test_set = data[:test_size]
    kb_set = data[test_size:]
    
    print(f"Split: {len(test_set)} Test, {len(kb_set)} KnowledgeBase")

    # Models
    # We only need Ours, but we run it with different alpha values
    rag_system = DualModalRAG(kb_set)
    evaluator = Evaluator()
    
    # Ablation Settings
    # alpha 0.0 = Text Only
    # alpha 0.5 = Dual (Both)
    # alpha 1.0 = Audio Only
    settings = {
        "TextOnly": 0.0,
        "AudioOnly": 1.0,
        "DualModal": 0.5
    }
    
    results = {
        "TextOnly": [],
        "AudioOnly": [],
        "DualModal": []
    }

    print("\n--- Running Experiments ---")
    for i, item in enumerate(test_set):
        song_name = item['SongName']
        gt_params = item['Parameters']
        
        # Prepare Inputs
        style_list = item.get('Style', [])
        feature_list = item.get('Feature', [])
        # Ensure lists
        if isinstance(style_list, str): style_list = [style_list]
        if isinstance(feature_list, str): feature_list = [feature_list]
        
        prompt_text = " ".join(style_list + feature_list)
        
        audio_vec = item['Vector']
        if isinstance(audio_vec, str):
             audio_vec = [float(x) for x in audio_vec.split(',')]

        print(f"[{i+1}/{len(test_set)}] {song_name}")

        for name, alpha in settings.items():
            pred = rag_system.retrieve(prompt_text, query_audio_vector=audio_vec, alpha=alpha)
            dist = evaluator.compute_parameter_distance(pred, gt_params)
            results[name].append(dist)

    # Summary
    print("\n--- Ablation Results Summary (Avg Parameter Distance) ---")
    summary = {}
    for name, scores in results.items():
        avg_dist = sum(scores) / len(scores)
        summary[name] = avg_dist
        print(f"{name}: {avg_dist:.4f}")

    # Interpretation
    print("\n--- Interpretation ---")
    if summary["DualModal"] < summary["TextOnly"] and summary["DualModal"] < summary["AudioOnly"]:
        print("DualModal improved over single modalities.")
    elif summary["AudioOnly"] < summary["TextOnly"]:
        print("Audio modality is stronger.")
    else:
        print("Text modality is stronger.")

    # Save
    out_path = os.path.join(os.path.dirname(__file__), 'results_ablation.json')
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    main()
