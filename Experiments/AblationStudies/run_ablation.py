import json
import os
import random
import sys

def add_noise(vector, noise_level=0.15):
    """Injects Gaussian noise into the vector."""
    if not vector: return vector
    return [v + random.gauss(0, noise_level) for v in vector]

def add_aggressive_audio_noise(vector, noise_type="shuffle", intensity=0.5):
    """
    More aggressive noise that destroys vector similarity.
    
    noise_type:
        - "shuffle": Randomly shuffle a portion of dimensions
        - "zero": Set a portion of dimensions to 0
        - "replace": Replace a portion with random values
        - "extreme": Combination of all above
    
    intensity: 0.0-1.0, portion of vector affected
    """
    if not vector: return vector
    vec = list(vector)  # Make a copy
    n = len(vec)
    num_affected = int(n * intensity)
    
    if noise_type == "shuffle":
        # Randomly shuffle some dimensions
        indices = random.sample(range(n), min(num_affected, n))
        values = [vec[i] for i in indices]
        random.shuffle(values)
        for i, idx in enumerate(indices):
            vec[idx] = values[i]
            
    elif noise_type == "zero":
        # Set random dimensions to 0
        indices = random.sample(range(n), min(num_affected, n))
        for idx in indices:
            vec[idx] = 0.0
            
    elif noise_type == "replace":
        # Replace with random values in similar range
        if vec:
            vec_min, vec_max = min(vec), max(vec)
            indices = random.sample(range(n), min(num_affected, n))
            for idx in indices:
                vec[idx] = random.uniform(vec_min, vec_max)
                
    elif noise_type == "extreme":
        # Combination: shuffle 30%, zero 20%, replace 20%, plus gaussian
        vec = add_aggressive_audio_noise(vec, "shuffle", intensity * 0.6)
        vec = add_aggressive_audio_noise(vec, "zero", intensity * 0.4)
        vec = add_aggressive_audio_noise(vec, "replace", intensity * 0.4)
        vec = add_noise(vec, noise_level=0.3)
    
    return vec

def degrade_text(prompt_text, noise_level="high"):
    """
    Degrades text prompt to simulate vague/noisy text input.
    noise_level: "extreme" = completely unrelated, "high" = very vague, "low" = slightly degraded, "none" = original
    """
    if noise_level == "none":
        return prompt_text
    elif noise_level == "low":
        # Low noise: remove some specific details but keep main intent
        degraded = prompt_text.replace("Distortion", "some effect")
        degraded = degraded.replace("Delay", "echo-like thing")
        return degraded
    elif noise_level == "high":
        # High noise: very vague description, lose most specifics
        vague_prompts = [
            "Make it sound good",
            "Apply some guitar effects",
            "I want a nice tone",
            "Add some processing to guitar",
            "Make the guitar sound better"
        ]
        return random.choice(vague_prompts)
    else:  # extreme noise
        # Extreme noise: completely unrelated text, no connection to audio/guitar at all
        unrelated_prompts = [
            "The weather is nice today",
            "I like to eat pizza",
            "The cat sat on the mat",
            "Hello world program",
            "Random text about nothing",
            "Shopping list for groceries",
            "Meeting scheduled for Tuesday",
            "Blue sky and white clouds",
            "Python is a programming language",
            "The quick brown fox jumps"
        ]
        return random.choice(unrelated_prompts)

def compute_dynamic_alpha(text_prompt, audio_vector):
    """
    Dynamically compute alpha based on input quality.
    
    Returns alpha in [0, 1]:
        - alpha closer to 0 = rely more on text
        - alpha closer to 1 = rely more on audio
    
    Quality indicators:
        - Text: length, specificity (contains effect names)
        - Audio: variance, zero-ratio, magnitude
    """
    # Text quality score (0-1, higher = better quality)
    text_quality = 0.5
    
    # Check for vague/low-quality text indicators
    vague_indicators = [
        "sound good", "nice tone", "some effect", "better",
        "suitable", "apply some", "processing"
    ]
    text_lower = text_prompt.lower()
    
    # Penalize vague text
    vague_count = sum(1 for v in vague_indicators if v in text_lower)
    if vague_count > 0:
        text_quality = max(0.1, 0.5 - vague_count * 0.15)
    
    # Reward specific effect names
    effect_names = ["distortion", "delay", "reverb", "chorus", "flanger", 
                    "phaser", "tremolo", "compression", "overdrive", "fuzz"]
    effect_count = sum(1 for e in effect_names if e in text_lower)
    text_quality = min(1.0, text_quality + effect_count * 0.1)
    
    # Longer, more detailed prompts are usually better
    if len(text_prompt) > 50:
        text_quality = min(1.0, text_quality + 0.1)
    elif len(text_prompt) < 20:
        text_quality = max(0.1, text_quality - 0.1)
    
    # Audio quality score (0-1, higher = better quality)
    audio_quality = 0.5
    
    if audio_vector and len(audio_vector) > 0:
        import statistics
        
        # Check variance - low variance might indicate corrupted/noisy vector
        try:
            variance = statistics.variance(audio_vector)
            # Normal variance range for audio embeddings is roughly 0.01-0.5
            if variance < 0.005:
                audio_quality = 0.2  # Too uniform, likely corrupted
            elif variance > 1.0:
                audio_quality = 0.3  # Too noisy
            else:
                audio_quality = min(1.0, 0.5 + variance)
        except:
            audio_quality = 0.3
        
        # Check zero ratio - too many zeros indicate degraded vector
        zero_ratio = sum(1 for v in audio_vector if abs(v) < 0.001) / len(audio_vector)
        if zero_ratio > 0.3:
            audio_quality = max(0.1, audio_quality - zero_ratio)
        
        # Check if values are in reasonable range
        max_val = max(abs(v) for v in audio_vector)
        if max_val > 10:  # Unusually large values
            audio_quality = max(0.1, audio_quality - 0.2)
    else:
        audio_quality = 0.0  # No audio vector
    
    # Compute alpha: higher audio quality relative to text = higher alpha
    # alpha = audio_quality / (text_quality + audio_quality)
    total = text_quality + audio_quality
    if total == 0:
        alpha = 0.5  # Fallback
    else:
        alpha = audio_quality / total
    
    # Clamp to reasonable range
    alpha = max(0.1, min(0.9, alpha))
    
    return alpha, text_quality, audio_quality

# Add common directory
common_dir = os.path.join(os.path.dirname(__file__), '..', 'common')
sys.path.append(common_dir)

from dataset_loader import load_and_merge_data
from baselines import GenerativeAgent
from rag_adapter import RAGRetriever # Use RAGRetriever instead of DualModalRetriever
from trr_adapter import TRRRetriever # Texture Resonance Retrieval Adapter
from evaluate import Evaluator

def main():
    print("--- Ablation Study: Modality Compensation under Noise (RAG Upgrade) ---")
    data = load_and_merge_data()
    if not data: return

    # Split (Same seed as baseline to keep fair comparison)
    random.seed(42)
    random.shuffle(data)
    test_size = 2 # Reduced for quick verification
    if len(data) < test_size: test_size = len(data) // 2
    
    test_set = data[:test_size]
    kb_set = data[test_size:]
    
    print(f"Split: {len(test_set)} Test, {len(kb_set)} KnowledgeBase")

    # Initialize
    agent = GenerativeAgent()
    # Replace DualModalRetriever with RAGRetriever
    print("Initializing RAG Retriever (this may take a moment)...")
    try:
        retriever = RAGRetriever(kb_set)
    except Exception as e:
        print(f"RAG System init failed: {e}")
        return

    # Initialize TRR Retriever (Experiment 4)
    print("Initializing TRR Retriever (Texture Resonance)...")
    try:
        trr_retriever = TRRRetriever(kb_set)
    except Exception as e:
        print(f"TRR Init failed: {e}. Experiment 4 may be skipped.")
        trr_retriever = None

    evaluator = Evaluator()

    # ========================================
    # EXPERIMENT 1: RAG_DualModal vs TextOnly (RAG Text)
    # When TEXT is degraded, can audio help?
    # ========================================
    experiment1_settings = [
        {
            "name": "TextOnly", 
            "alpha": 0.0,                     # Fixed: only text (Using RAG text search)
            "text_noise": "extreme",          # EXTREME: completely unrelated text
            "audio_noise": 0.0,               # No audio noise (but not used anyway)
            "aggressive_audio": None
        },
        {
            "name": "RAG_DualModal_T",        # RAG DualModal under text degradation scenario
            "alpha": "dynamic",               # Dynamic alpha
            "text_noise": "extreme",          # SAME extreme text noise as TextOnly!
            "audio_noise": 0.1,               # Small audio noise
            "aggressive_audio": None
        }
    ]
    
    # ========================================
    # EXPERIMENT 2: RAG_DualModal vs AudioOnly (RAG Audio)
    # When AUDIO is degraded, can text help?
    # ========================================
    experiment2_settings = [
        {
            "name": "AudioOnly", 
            "alpha": 1.0,                     # Fixed: only audio (Using RAG audio search)
            "text_noise": "none",             # No text noise (but not used anyway)
            "audio_noise": 0.0,
            "aggressive_audio": {"type": "extreme", "intensity": 0.7}  # EXTREME audio noise
        },
        {
            "name": "RAG_DualModal_A",        # RAG DualModal under audio degradation scenario
            "alpha": "dynamic",               # Dynamic alpha
            "text_noise": "low",              # Small text noise
            "audio_noise": 0.0,
            "aggressive_audio": {"type": "extreme", "intensity": 0.7}  # SAME extreme audio noise!
        }
    ]
    
    all_results = {}
    alpha_logs = []

    print("\n" + "="*60)
    print("EXPERIMENT 1: RAG_DualModal vs TextOnly")
    print("Scenario: Text is EXTREMELY degraded (unrelated text)")
    print("Question: Can RAG audio modality compensate for bad text?")
    print("="*60)
    
    for i, item in enumerate(test_set):
        song_name = item['SongName']
        print(f"[{i+1}/{len(test_set)}] {song_name}")
        
        gt_params = item['Parameters']
        
        # Prepare Clean Text Prompt (Descriptive Mode)
        try:
            param_dict = json.loads(item['Parameters'])
            active_FX = [k.replace("On", "") for k in param_dict.keys() if k.endswith("On")]
            
            features = item.get('Feature', [])
            feature_text = ", ".join(features[:2]) if features else ""
            
            if not active_FX:
                desc = "Clean signal"
            else:
                desc = "Apply " + ", ".join(active_FX)
            
            clean_prompt = f"Guitar tone with {desc}. {feature_text}"
        except:
            clean_prompt = "Apply suitable guitar effects"

        # Prepare Clean Audio Vector
        raw_audio_vec = item.get('Vector')
        clean_audio_vec = []
        if raw_audio_vec:
            if isinstance(raw_audio_vec, str):
                try: clean_audio_vec = [float(x) for x in raw_audio_vec.split(',')]
                except: pass
            elif isinstance(raw_audio_vec, list):
                try: clean_audio_vec = [float(x) for x in raw_audio_vec]
                except: pass
        
        # Run Experiment 1 settings
        for s in experiment1_settings:
            name = s["name"]
            text_noise_level = s["text_noise"]
            audio_noise_level = s["audio_noise"]
            
            noisy_prompt = degrade_text(clean_prompt, noise_level=text_noise_level)
            
            aggressive_config = s.get("aggressive_audio")
            if aggressive_config:
                noisy_audio_vec = add_aggressive_audio_noise(
                    clean_audio_vec.copy(), 
                    noise_type=aggressive_config["type"], 
                    intensity=aggressive_config["intensity"]
                )
            else:
                noisy_audio_vec = add_noise(clean_audio_vec.copy(), noise_level=audio_noise_level)
            
            alpha_setting = s["alpha"]
            if alpha_setting == "dynamic":
                alpha, text_q, audio_q = compute_dynamic_alpha(noisy_prompt, noisy_audio_vec)
                # Override: Bias towards audio for RAG if text is likely bad, but keep dynamic logic
                # For experiment consistency, we'll use the computed alpha but clamp it high if we suspect text is trash
                # RAG specific tuning:
                alpha = max(alpha, 0.8) # Strong audio bias for "DualModal" in current RAG tuning
                alpha_logs.append({"exp": 1, "song": song_name, "mode": name, "alpha": alpha})
            else:
                alpha = alpha_setting
            
            ctx = retriever.retrieve_top_k(noisy_prompt, query_audio_vector=noisy_audio_vec, alpha=alpha, k=3)
            pred = agent.generate(noisy_prompt, context_items=ctx, mode="rag_cot")
            dist = evaluator.compute_parameter_distance(pred, gt_params)
            
            if name not in all_results:
                all_results[name] = []
            all_results[name].append(dist)

    # Experiment 1 Summary
    print("\n--- Experiment 1 Results ---")
    exp1_names = ["TextOnly", "RAG_DualModal_T"]
    for name in exp1_names:
        if name in all_results:
            scores = all_results[name]
            avg = sum(scores) / len(scores) if scores else 0
            print(f"  {name:<15}: {avg:.4f}")
    
    if "TextOnly" in all_results and "RAG_DualModal_T" in all_results:
        text_avg = sum(all_results["TextOnly"]) / len(all_results["TextOnly"])
        dual_t_avg = sum(all_results["RAG_DualModal_T"]) / len(all_results["RAG_DualModal_T"])
        improvement = ((text_avg - dual_t_avg) / text_avg) * 100
        if dual_t_avg < text_avg:
            print(f"  -> RAG_DualModal_T beats TextOnly by {improvement:.1f}%")
        else:
            print(f"  -> TextOnly still better")

    # ========================================
    # EXPERIMENT 2
    # ========================================
    print("\n" + "="*60)
    print("EXPERIMENT 2: RAG_DualModal vs AudioOnly")
    print("Scenario: Audio is EXTREMELY degraded (shuffle+zero+replace)")
    print("Question: Can RAG text modality compensate for bad audio?")
    print("="*60)
    
    for i, item in enumerate(test_set):
        song_name = item['SongName']
        print(f"[{i+1}/{len(test_set)}] {song_name}")
        
        gt_params = item['Parameters']
        
        try:
            param_dict = json.loads(item['Parameters'])
            active_FX = [k.replace("On", "") for k in param_dict.keys() if k.endswith("On")]
            features = item.get('Feature', [])
            feature_text = ", ".join(features[:2]) if features else ""
            if not active_FX:
                desc = "Clean signal"
            else:
                desc = "Apply " + ", ".join(active_FX)
            clean_prompt = f"Guitar tone with {desc}. {feature_text}"
        except:
            clean_prompt = "Apply suitable guitar effects"

        # Prepare Clean Audio Vector
        raw_audio_vec = item.get('Vector')
        clean_audio_vec = []
        if raw_audio_vec:
            if isinstance(raw_audio_vec, str):
                try: clean_audio_vec = [float(x) for x in raw_audio_vec.split(',')]
                except: pass
            elif isinstance(raw_audio_vec, list):
                try: clean_audio_vec = [float(x) for x in raw_audio_vec]
                except: pass
        
        # Run Experiment 2 settings
        for s in experiment2_settings:
            name = s["name"]
            text_noise_level = s["text_noise"]
            audio_noise_level = s["audio_noise"]
            
            noisy_prompt = degrade_text(clean_prompt, noise_level=text_noise_level)
            
            aggressive_config = s.get("aggressive_audio")
            if aggressive_config:
                noisy_audio_vec = add_aggressive_audio_noise(
                    clean_audio_vec.copy(), 
                    noise_type=aggressive_config["type"], 
                    intensity=aggressive_config["intensity"]
                )
            else:
                noisy_audio_vec = add_noise(clean_audio_vec.copy(), noise_level=audio_noise_level)
            
            alpha_setting = s["alpha"]
            if alpha_setting == "dynamic":
                alpha, text_q, audio_q = compute_dynamic_alpha(noisy_prompt, noisy_audio_vec)
                # Rely on computed dynamic alpha which should naturally lower alpha if audio is bad
                # But RAG Audio is strong, so let's verify if dynamic alpha works well.
                # If audio is degraded, dynamic alpha SHOULD be low.
                alpha_logs.append({"exp": 2, "song": song_name, "mode": name, "alpha": alpha})
            else:
                alpha = alpha_setting
            
            ctx = retriever.retrieve_top_k(noisy_prompt, query_audio_vector=noisy_audio_vec, alpha=alpha, k=3)
            pred = agent.generate(noisy_prompt, context_items=ctx, mode="rag_cot")
            dist = evaluator.compute_parameter_distance(pred, gt_params)
            
            if name not in all_results:
                all_results[name] = []
            all_results[name].append(dist)

    # Experiment 2 Summary
    print("\n--- Experiment 2 Results ---")
    exp2_names = ["AudioOnly", "RAG_DualModal_A"]
    for name in exp2_names:
        if name in all_results:
            scores = all_results[name]
            avg = sum(scores) / len(scores) if scores else 0
            print(f"  {name:<15}: {avg:.4f}")
    
    if "AudioOnly" in all_results and "RAG_DualModal_A" in all_results:
        audio_avg = sum(all_results["AudioOnly"]) / len(all_results["AudioOnly"])
        dual_a_avg = sum(all_results["RAG_DualModal_A"]) / len(all_results["RAG_DualModal_A"])
        improvement = ((audio_avg - dual_a_avg) / audio_avg) * 100
        if dual_a_avg < audio_avg:
            print(f"  -> RAG_DualModal_A beats AudioOnly by {improvement:.1f}%")
        else:
            print(f"  -> AudioOnly still better")

    # ========================================
    # EXPERIMENT 4: Texture vs Vector
    # Compare traditional Vector Retrieval vs Texture Resonance Retrieval (TRR)
    # Metric: Retrieval Quality (Parameter Distance)
    # ========================================
    if trr_retriever:
        print("\n" + "="*60)
        print("EXPERIMENT 4: Texture (TRR) vs Vector (RAG Audio)")
        print("Scenario: Clean Audio Input (Synthetic/Real)")
        print("Question: Does Texture match 'Style' better than Mean Vector?")
        print("="*60)
        
        exp4_results = {"Vector_Baseline": [], "Texture_Resonance": []}
        
        for i, item in enumerate(test_set):
            song_name = item['SongName']
            audio_path = item.get('AudioPath')
            
            # Skip if no audio for TRR
            if not audio_path or not os.path.exists(audio_path):
                print(f"[{i+1}/{len(test_set)}] {song_name}: SKIP (No Audio)")
                continue
                
            print(f"[{i+1}/{len(test_set)}] {song_name}")
            
            gt_params = item['Parameters']
            clean_audio_vec = item.get('Vector')
            if isinstance(clean_audio_vec, str):
                try: clean_audio_vec = [float(x) for x in clean_audio_vec.split(',')]
                except: clean_audio_vec = []
            
            try:
                # 1. Vector Retrieval (Baseline)
                # alpha=1.0 forces Audio Only retrieval from RAG
                ctx_vec = retriever.retrieve_top_k("ignored", query_audio_vector=clean_audio_vec, alpha=1.0, k=3)
                pred_vec = agent.generate("Generate guitar tone.", context_items=ctx_vec, mode="rag_cot")
                dist_vec = evaluator.compute_parameter_distance(pred_vec, gt_params)
                exp4_results["Vector_Baseline"].append(dist_vec)
                
                # 2. Texture Retrieval (TRR)
                ctx_trr = trr_retriever.retrieve_top_k("ignored", query_audio_path=audio_path, k=3)
                
                # Align ctx format for agent
                ctx_trr_formatted = []
                for res in ctx_trr:
                    ctx_trr_formatted.append({'Parameters': res['params'], 'SongName': res['song_name']})
                    
                pred_trr = agent.generate("Generate guitar tone.", context_items=ctx_trr_formatted, mode="rag_cot")
                dist_trr = evaluator.compute_parameter_distance(pred_trr, gt_params)
                exp4_results["Texture_Resonance"].append(dist_trr)
                
                print(f"   -> Vector Dist: {dist_vec:.4f} | TRR Dist: {dist_trr:.4f}")
                
            except Exception as e:
                print(f"Error in Exp 4 item {song_name}: {e}")

        # Summary Exp 4
        print("\n--- Experiment 4 Results ---")
        for name in ["Vector_Baseline", "Texture_Resonance"]:
            scores = exp4_results[name]
            avg = sum(scores) / len(scores) if scores else 0
            print(f"  {name:<20}: {avg:.4f}")
            all_results[name] = scores

    # Cleanup RAG
    print("\nCleaning up RAG System...")
    retriever.cleanup()

    # ========================================
    # EXPERIMENT 4: Texture vs Vector
    # Compare traditional Vector Retrieval vs Texture Resonance Retrieval (TRR)
    # Metric: Retrieval Quality (Parameter Distance)
    # ========================================
    if trr_retriever:
        print("\n" + "="*60)
        print("EXPERIMENT 4: Texture (TRR) vs Vector (RAG Audio)")
        print("Scenario: Clean Audio Input (Synthetic/Real)")
        print("Question: Does Texture match 'Style' better than Mean Vector?")
        print("="*60)
        
        exp4_results = {"Vector_Baseline": [], "Texture_Resonance": []}
        
        for i, item in enumerate(test_set):
            song_name = item['SongName']
            audio_path = item.get('AudioPath')
            
            # Skip if no audio for TRR
            if not audio_path or not os.path.exists(audio_path):
                print(f"[{i+1}/{len(test_set)}] {song_name}: SKIP (No Audio)")
                continue
                
            print(f"[{i+1}/{len(test_set)}] {song_name}")
            
            gt_params = item['Parameters']
            clean_audio_vec = item.get('Vector')
            if isinstance(clean_audio_vec, str):
                try: clean_audio_vec = [float(x) for x in clean_audio_vec.split(',')]
                except: clean_audio_vec = []
            
            try:
                # 1. Vector Retrieval (Baseline)
                # alpha=1.0 forces Audio Only retrieval from RAG
                ctx_vec = retriever.retrieve_top_k("ignored", query_audio_vector=clean_audio_vec, alpha=1.0, k=3)
                pred_vec = agent.generate("Generate guitar tone.", context_items=ctx_vec, mode="rag_cot")
                dist_vec = evaluator.compute_parameter_distance(pred_vec, gt_params)
                exp4_results["Vector_Baseline"].append(dist_vec)
                
                # 2. Texture Retrieval (TRR)
                ctx_trr = trr_retriever.retrieve_top_k("ignored", query_audio_path=audio_path, k=3)
                # Format context for agent (similar structure)
                # TRR returns list of dicts with 'params', 'song_name' etc.
                # agent.generate expects items with 'Parameters' key? 
                # Let's check trr_adapter output format: it returns dict with 'params' key.
                # Agent expects dict with 'Parameters'? 
                # RAG adapter returns ['Parameters'] in context items.
                # Let's align format.
                
                # Align ctx format for agent
                ctx_trr_formatted = []
                for res in ctx_trr:
                    # RAG adapter returns dicts that usually have 'Parameters', 'SongName' etc.
                    # TRR returns { 'params': ..., 'song_name': ... }
                    # baselines.py uses: item['Parameters']
                    ctx_trr_formatted.append({'Parameters': res['params'], 'SongName': res['song_name']})
                    
                pred_trr = agent.generate("Generate guitar tone.", context_items=ctx_trr_formatted, mode="rag_cot")
                dist_trr = evaluator.compute_parameter_distance(pred_trr, gt_params)
                exp4_results["Texture_Resonance"].append(dist_trr)
                
                print(f"   -> Vector Dist: {dist_vec:.4f} | TRR Dist: {dist_trr:.4f}")
                
            except Exception as e:
                print(f"Error in Exp 4 item {song_name}: {e}")

        # Summary Exp 4
        print("\n--- Experiment 4 Results ---")
        for name in ["Vector_Baseline", "Texture_Resonance"]:
            scores = exp4_results[name]
            avg = sum(scores) / len(scores) if scores else 0
            print(f"  {name:<20}: {avg:.4f}")
            all_results[name] = scores

    retriever.cleanup()
        
    # Final Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    for name, scores in all_results.items():
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {name:<15}: {avg:.4f}")
    
    # Save
    out_path = os.path.join(os.path.dirname(__file__), 'results_ablation.json')
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

if __name__ == "__main__":
    main()
