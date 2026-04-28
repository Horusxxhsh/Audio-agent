"""
Pseudo-User Simulation Framework for Adaptive Audio-Agent
模拟人类对检索结果的微调反馈，验证 Memory 模块的收敛性。
"""

import os
import json
import numpy as np
import time
import matplotlib.pyplot as plt
from rag_system import AudioRAGSystem, initialize_knowledge_base
from typing import List, Dict, Any, Tuple

class UserSimulator:
    """伪用户仿真器"""
    
    def __init__(self, rag_system: AudioRAGSystem):
        self.rag = rag_system
        
    def simulate_tweak(self, current_params: Dict[str, Any], target_params: Dict[str, Any], learning_rate: float = 0.5) -> Dict[str, Any]:
        """
        模拟用户微调行为：将当前参数向目标参数移动一部分。
        Formula: theta_new = (1 - alpha) * theta_current + alpha * theta_target
        """
        new_params = {}
        for key in target_params:
            if key in current_params and isinstance(current_params[key], (int, float)):
                # 线性插值
                new_params[key] = (1.0 - learning_rate) * current_params[key] + learning_rate * target_params[key]
            else:
                # 非数值参数直接取目标值（模拟用户选择了正确模块）
                new_params[key] = target_params[key]
        return new_params

    def calculate_l2_error(self, p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
        """计算两个参数集之间的归一化 L2 距离"""
        keys = set(p1.keys()) | set(p2.keys())
        v1, v2 = [], []
        for k in keys:
            if isinstance(p1.get(k), (int, float)) and isinstance(p2.get(k), (int, float)):
                v1.append(p1[k])
                v2.append(p2[k])
        
        if not v1: return 1.0
        v1, v2 = np.array(v1), np.array(v2)
        return np.linalg.norm(v1 - v2) / (np.sqrt(len(v1)) + 1e-6)

def run_convergence_experiment(n_turns: int = 5):
    """运行个性化收敛实验"""
    print("\n" + "="*60)
    print(f"Running Personalization Convergence Experiment ({n_turns} turns)")
    print("="*60)
    
    # 1. Initialize System
    rag = AudioRAGSystem(
        api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
        base_url="https://api.deepseek.com"
    )
    initialize_knowledge_base(rag)
    simulator = UserSimulator(rag)
    
    # 预填充一些基础预设到 KB，确保第一轮有结果
    rag.add_parameter_preset(
        preset_name="Standard Funk",
        parameters={"gain": 0.5, "comp_threshold": -15.0, "reverb_mix": 0.05, "eq_treble": 0.5},
        style_tags=["funk", "clean"],
        description="A standard clean funk guitar preset",
        audio_vector=np.random.rand(384).tolist()
    )
    rag.add_parameter_preset(
        preset_name="Bright Pop",
        parameters={"gain": 0.3, "comp_threshold": -20.0, "reverb_mix": 0.1, "eq_treble": 0.9},
        style_tags=["pop", "clean", "bright"],
        description="Bright pop guitar tone",
        audio_vector=np.random.rand(384).tolist()
    )
    
    # 清空旧记忆以开始干净的实验
    try:
        rag.chroma_client.delete_collection("user_preference_memory")
        rag.memory_collection = rag._get_or_create_collection("user_preference_memory")
    except:
        pass

    # 2. Setup Target (A specific "Clean Funk" tone with a custom offset)
    # We use a synthetic audio vector (random but fixed for this test)
    np.random.seed(42)
    test_audio_vector = np.random.rand(384).tolist() 
    test_query = "tight clean funk guitar"
    
    # Ideal target parameters (Ground Truth + Bias)
    target_params = {
        "gain": 0.2,
        "comp_threshold": -24.0,
        "reverb_mix": 0.15,
        "eq_treble": 0.8,
        "delay_feedback": 0.0
    }
    
    results = []
    
    # 3. Iterative Loop
    for turn in range(1, n_turns + 1):
        print(f"\n>>> Turn {turn}:")
        
        # Step A: Retrieval
        recommendations = rag.recommend_parameters(
            style_tags=["funk", "clean"],
            user_description=test_query,
            n_recommendations=1,
            audio_query_vector=test_audio_vector
        )
        
        if not recommendations:
            print("No recommendations found!")
            break
            
        top_res = recommendations[0]
        retrieved_params = top_res['parameters']
        source = top_res.get('source_modality', 'kb')
        
        # Step B: Evaluate current error
        error = simulator.calculate_l2_error(retrieved_params, target_params)
        print(f"   Retrieved from: {source}")
        print(f"   L2 Error: {error:.4f}")
        
        # Step C: Simulate User Feedback (Tweak)
        # In Turn 1, user tweaks the result. In subsequent turns, they might just accept if good enough.
        new_params = simulator.simulate_tweak(retrieved_params, target_params, learning_rate=0.6)
        
        # Step D: Save to Memory
        rag.save_to_memory(
            query=test_query,
            parameters=new_params,
            audio_vector=test_audio_vector
        )
        
        results.append({
            "turn": turn,
            "error": error,
            "source": source
        })
        
    return results

def plot_results(results: List[Dict[str, Any]], output_path: str):
    """绘制收敛曲线图"""
    turns = [r['turn'] for r in results]
    errors = [r['error'] for r in results]
    
    plt.figure(figsize=(10, 6))
    plt.plot(turns, errors, marker='o', linestyle='-', linewidth=2, color='#2c3e50', label='Adaptive Memory RAG')
    
    # Plot a horizontal line for baseline (Turn 1 error repeated)
    plt.axhline(y=errors[0], color='#e74c3c', linestyle='--', label='Static RAG Baseline')
    
    plt.title('Personalization Convergence: L2 Error vs. Interaction Turns', fontsize=14)
    plt.xlabel('Turn Number', fontsize=12)
    plt.ylabel('L2 Distance to User Preference', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.ylim(0, max(errors) * 1.2)
    
    plt.savefig(output_path)
    print(f"\nPlot saved to {output_path}")

def run_generalization_experiment():
    """运行跨会话泛化实验"""
    print("\n" + "="*60)
    print("Running Cross-Session Generalization Experiment")
    print("="*60)
    
    rag = AudioRAGSystem(api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""), base_url="https://api.deepseek.com")
    simulator = UserSimulator(rag)
    
    # 1. Session 1: Learn preference for Audio A
    print("\n>>> Session 1: Learning preference for Audio A")
    audio_a = (np.random.rand(384) * 0.5).tolist()
    query_a = "warm overdrive guitar"
    target_params = {"gain": 0.7, "drive": 0.8, "tone": 0.4}
    
    # Initial retrieval and tweak
    recs = rag.recommend_parameters(["overdrive"], query_a, audio_query_vector=audio_a)
    tuned_params = simulator.simulate_tweak(recs[0]['parameters'], target_params, learning_rate=1.0)
    rag.save_to_memory(query_a, tuned_params, audio_a, metadata={"session": "1", "audio_label": "A"})
    
    # 2. Session 2: Test on Audio B (highly similar to A)
    print("\n>>> Session 2: Testing on similar Audio B")
    # Add small noise to A to create B
    audio_b = (np.array(audio_a) + np.random.normal(0, 0.01, 384)).tolist()
    query_b = "warm overdrive guitar" # Same query
    
    recs_b = rag.recommend_parameters(["overdrive"], query_b, audio_query_vector=audio_b)
    top_b = recs_b[0]
    
    print(f"   Input B Similarity to Memory A: {top_b.get('similarity', 0):.4f}")
    print(f"   Retrieved from: {top_b.get('source_modality')}")
    
    is_hit = top_b.get('source_modality') == 'memory'
    print(f"   Generalization Hit: {is_hit}")
    
    return is_hit

def run_ablation_experiment():
    """运行索引策略消融实验"""
    print("\n" + "="*60)
    print("Running Indexing Strategy Ablation Experiment")
    print("="*60)
    
    rag = AudioRAGSystem(api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""), base_url="https://api.deepseek.com")
    
    # Setup test case
    audio_ref = np.random.rand(384).tolist()
    text_ref = "crunchy blues lead"
    params_ref = {"gain": 0.6, "reverb": 0.3}
    
    # Save to memory using TRR (Gram Matrix) as index
    rag.save_to_memory(text_ref, params_ref, audio_ref, metadata={"tag": "ablation_ref"})
    
    # Test 1: Search with Text Only (no audio vector)
    print("\n>>> Strategy 1: Text-only indexing")
    res_text = rag.retrieve_similar_knowledge(text_ref, collection_type="parameter", audio_query_vector=None)
    found_in_mem = any(r.get('source_modality') == 'memory' for r in res_text)
    print(f"   Memory Found: {found_in_mem}")
    
    # Test 2: Search with TRR (Gram Matrix)
    print("\n>>> Strategy 2: TRR (Gram Matrix) indexing")
    # Add noise to simulate slightly different but same texture input
    audio_test = (np.array(audio_ref) + np.random.normal(0, 0.05, 384)).tolist()
    res_trr = rag.retrieve_similar_knowledge(text_ref, collection_type="parameter", audio_query_vector=audio_test)
    found_in_mem_trr = any(r.get('source_modality') == 'memory' for r in res_trr)
    sim = res_trr[0].get('score', 0) if res_trr else 0
    print(f"   Memory Found: {found_in_mem_trr} (Similarity: {sim:.4f})")
    
    return found_in_mem, found_in_mem_trr

if __name__ == "__main__":
    # ... existing main
    run_ablation_experiment()
