import json
import os
import random
import sys
import statistics
import time

# Add common directory
common_dir = os.path.join(os.path.dirname(__file__), '..', 'common')
sys.path.append(common_dir)

from dataset_loader import load_and_merge_data
from baselines import GenerativeAgent
from rag_adapter import RAGRetriever 
from trr_adapter import TRRRetriever 
from evaluate import Evaluator

# ==========================================
# Helper Functions (Noise & Dynamic Weight)
# ==========================================

def compute_dynamic_alpha(text_prompt, audio_vector):
    """
    Dynamically compute alpha based on input quality.
    alpha in [0, 1]. High alpha = rely more on Audio.
    """
    # Text quality score
    text_quality = 0.5
    vague_indicators = ["sound good", "nice tone", "some effect", "better", "suitable", "processing"]
    text_lower = text_prompt.lower()
    
    if any(v in text_lower for v in vague_indicators):
        text_quality = 0.2
    
    effect_names = ["distortion", "delay", "reverb", "chorus", "flanger", "phaser", "tremolo", "compression"]
    if any(e in text_lower for e in effect_names):
        text_quality = min(1.0, text_quality + 0.3)
    
    # Audio quality score
    audio_quality = 0.5
    if audio_vector and len(audio_vector) > 0:
        try:
            var = statistics.variance(audio_vector)
            if var < 0.005: audio_quality = 0.2 # flat
            elif var > 1.0: audio_quality = 0.2 # noisy
            else: audio_quality = 0.8 # good
        except:
            audio_quality = 0.3
    else:
        audio_quality = 0.0

    # Fusion
    total = text_quality + audio_quality
    if total == 0: return 0.5
    alpha = audio_quality / total
    return max(0.1, min(0.9, alpha))

def degrade_text_prompt(prompt):
    return "Make it sound good with some effects."

# ==========================================
# Main Experiment Script
# ==========================================

def main():
    print("================================================================")
    print("   Neuro-Symbolic Audio Agent - Top-Tier Journal Experiments    ")
    print("================================================================")
    
    # 1. Load Data
    data = load_and_merge_data()
    if not data: return
    
    # Split
    random.seed(42)
    random.shuffle(data)
    test_size = 5 # Small test set for demo speed
    if len(data) < test_size: test_size = len(data) // 2
    
    test_set = data[:test_size]
    kb_set = data[test_size:]
    print(f"Dataset Split: {len(test_set)} Test, {len(kb_set)} KnowledgeBase")

    # 2. Init Models
    print("\n--- Initializing Retrievers ---")
    agent = GenerativeAgent()
    evaluator = Evaluator()
    
    try:
        rag = RAGRetriever(kb_set)
        print(">> RAG System (Text/Vector) Ready.")
    except Exception as e:
        print(f"!! RAG Init Failed: {e}")
        return

    try:
        trr = TRRRetriever(kb_set)
        print(">> TRR System (Texture Resonance) Ready.")
    except Exception as e:
        print(f"!! TRR Init Failed: {e}")
        trr = None

    # Storage for Results
    results = {
        "B1_ZeroShot": [],
        "B2_TextRAG": [],
        "B3_VectorRAG": [],
        "Ours_TextureRAG": [],
        "Ablation_Noise_TextOnly": [],
        "Ablation_Noise_Ours": []
    }

    # ==========================================
    # RQ1: Effectiveness (Main Performance)
    # Compare B1, B2, B3, Ours on Clean Data
    # ==========================================
    print("\n[Running Experiment 1: Effectiveness]")
    
    for i, item in enumerate(test_set):
        name = item['SongName']
        gt_params = item['Parameters']
        
        # Inputs
        text_prompt = f"Guitar tone for {name}. {', '.join(item.get('Feature', [])[:2])}"
        audio_vec = item.get('Vector')
        audio_path = item.get('AudioPath')
        
        if isinstance(audio_vec, str):
             try: audio_vec = [float(x) for x in audio_vec.split(',')]
             except: audio_vec = []

        print(f"\nProcessing {name}...")

        # --- B1: Zero-shot ---
        pred_b1 = agent.generate(text_prompt, mode="zero_shot")
        dist_b1 = evaluator.compute_parameter_distance(pred_b1, gt_params)
        results["B1_ZeroShot"].append(dist_b1)

        # --- B2: Text-RAG (Alpha=0.0) ---
        ctx_b2 = rag.retrieve_top_k(text_prompt, query_audio_vector=None, alpha=0.0, k=3)
        pred_b2 = agent.generate(text_prompt, context_items=ctx_b2, mode="rag_cot")
        dist_b2 = evaluator.compute_parameter_distance(pred_b2, gt_params)
        results["B2_TextRAG"].append(dist_b2)

        # --- B3: Vector-RAG (Alpha=1.0) ---
        ctx_b3 = rag.retrieve_top_k("ignored", query_audio_vector=audio_vec, alpha=1.0, k=3)
        pred_b3 = agent.generate(text_prompt, context_items=ctx_b3, mode="rag_cot") # Prompt still needed for generation
        dist_b3 = evaluator.compute_parameter_distance(pred_b3, gt_params)
        results["B3_VectorRAG"].append(dist_b3)

        # --- Ours: Texture-RAG (Dual + TRR) ---
        # Strategy: Get Text Candidates + Texture Candidates -> Fuse
        # 1. Text Candidates from RAG
        ctx_text = rag.retrieve_top_k(text_prompt, alpha=0.0, k=3)
        
        # 2. Texture Candidates from TRR (if available)
        ctx_texture = []
        if trr and audio_path and os.path.exists(audio_path):
            trr_res = trr.retrieve_top_k("ignored", query_audio_path=audio_path, k=3)
            # Reformat to match RAG output structure
            for r in trr_res:
                ctx_texture.append({'Parameters': r['params'], 'SongName': r['song_name'], 'Score': r['score']})
        else:
            # Fallback to Vector RAG if TRR not possible
            ctx_texture = ctx_b3 

        # 3. Simple Fusion (Combine and Dedup)
        # In a real dynamic system we would weight them, here we just take unique union for context
        combined_ctx = ctx_text + ctx_texture
        # Dedup by song name
        seen = set()
        final_ctx = []
        for c in combined_ctx:
            s_name = c.get('SongName')
            if s_name not in seen:
                seen.add(s_name)
                final_ctx.append(c)
        
        pred_ours = agent.generate(text_prompt, context_items=final_ctx[:5], mode="rag_cot")
        dist_ours = evaluator.compute_parameter_distance(pred_ours, gt_params)
        results["Ours_TextureRAG"].append(dist_ours)
        
        print(f"  -> Distances | B1: {dist_b1:.2f} | B2: {dist_b2:.2f} | B3: {dist_b3:.2f} | Ours: {dist_ours:.2f}")

    # ==========================================
    # RQ3: Robustness (Ablation under Noise)
    # Scenario: Vague Text ("Make it sound good")
    # Compare Text-Only RAG vs Ours (should shift to Audio)
    # ==========================================
    print("\n[Running Experiment 3: Robustness (Vague Text)]")
    
    for item in test_set:
        gt_params = item['Parameters']
        audio_path = item.get('AudioPath')
        
        clean_prompt = f"Guitar tone for {item['SongName']}"
        noisy_prompt = degrade_text_prompt(clean_prompt) # "Make it sound good..."

        # 1. Baseline: Text RAG (Will fail because text is vague)
        ctx_noise_b2 = rag.retrieve_top_k(noisy_prompt, alpha=0.0, k=3)
        pred_noise_b2 = agent.generate(noisy_prompt, context_items=ctx_noise_b2, mode="rag_cot")
        dist_noise_b2 = evaluator.compute_parameter_distance(pred_noise_b2, gt_params)
        results["Ablation_Noise_TextOnly"].append(dist_noise_b2)
        
        # 2. Ours: TRR (Should rely on audio texture despite bad text)
        if trr and audio_path and os.path.exists(audio_path):
            ctx_noise_ours = trr.retrieve_top_k("ignored", query_audio_path=audio_path, k=3)
            # Format
            ctx_formatted = [{'Parameters': r['params'], 'SongName': r['song_name']} for r in ctx_noise_ours]
            pred_noise_ours = agent.generate(noisy_prompt, context_items=ctx_formatted, mode="rag_cot")
        else:
             # Fallback to vector rag
             audio_vec = item.get('Vector')
             if isinstance(audio_vec, str): audio_vec = [float(x) for x in audio_vec.split(',')]
             ctx_noise_ours = rag.retrieve_top_k(noisy_prompt, query_audio_vector=audio_vec, alpha=1.0, k=3)
             pred_noise_ours = agent.generate(noisy_prompt, context_items=ctx_noise_ours, mode="rag_cot")
             
        dist_noise_ours = evaluator.compute_parameter_distance(pred_noise_ours, gt_params)
        results["Ablation_Noise_Ours"].append(dist_noise_ours)


    # ==========================================
    # Summary Report
    # ==========================================
    print("\n" + "="*60)
    print("FINAL JOURNAL EXPERIMENT RESULTS")
    print("="*60)
    
    print("RQ1: Main Effectiveness (Lower Distance is Better)")
    print(f"  B1 (Zero-shot)  : {statistics.mean(results['B1_ZeroShot']):.4f}")
    print(f"  B2 (Text-RAG)   : {statistics.mean(results['B2_TextRAG']):.4f}")
    print(f"  B3 (Vector-RAG) : {statistics.mean(results['B3_VectorRAG']):.4f}")
    print(f"  Ours (Texture)  : {statistics.mean(results['Ours_TextureRAG']):.4f}")
    
    print("\nRQ3: Robustness under Vague Text")
    print(f"  Text-Only RAG   : {statistics.mean(results['Ablation_Noise_TextOnly']):.4f}")
    print(f"  Ours (Texture)  : {statistics.mean(results['Ablation_Noise_Ours']):.4f}")

    # Cleanup
    rag.cleanup()

if __name__ == "__main__":
    main()
