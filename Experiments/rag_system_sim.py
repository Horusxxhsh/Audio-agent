import json
import math
import random

# For real implementation, valid vector math needed (numpy)
# Since we might not have numpy, we'll write a simple cosine sim helper
def cosine_similarity(v1, v2):
    dot_product = sum(a*b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a*a for a in v1))
    magnitude2 = math.sqrt(sum(b*b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

class DualModalRAG:
    """
    Simulated Dual-Modal RAG (Audio-Agent Ours)
    Combines Text Similarity + Audio Similarity.
    
    Since we don't have a live text embedder running generally, we will:
    1. Simulate Text Similarity (random or via simple word overlap if needed, 
       but for this 'Sim', we assume we have scores).
    2. Use Real Audio Similarity (via cosine on 'Vector' field).
    """
    def __init__(self, training_data):
        self.training_data = training_data
        # Ensure vectors are list of floats
        self.knowledge_base = []
        for item in training_data:
            vec_str = item.get('Vector', "")
            try:
                # If vector is string "0.1, 0.2, ...", parse it
                if isinstance(vec_str, str):
                    vec = [float(x) for x in vec_str.split(',')]
                else:
                    vec = vec_str # Assume already list
                
                self.knowledge_base.append({
                    "item": item,
                    "vector": vec
                })
            except:
                # print("Warning: Failed to parse vector")
                pass

    def retrieve(self, query_text, query_audio_vector=None, alpha=0.5):
        """
        Retrieves best match.
        alpha: Weight for Audio Similarity (0.0 = Text Only, 1.0 = Audio Only)
        
        If query_audio_vector is None, falls back to text only (alpha=0).
        For simulation without real Text embeddings:
        - We will assume 'Text Similarity' is 0.5 for everything (acting as a neutral prior)
          OR we can implement a weak text match (keyword overlap).
        """
        
        scores = []
        
        for kb_item in self.knowledge_base:
            # 1. Text Score (Heuristic: Keyword Overlap)
            # A real system would use Embedding Cosine Similarity
            kb_txt = " ".join(kb_item["item"].get("Style", []) + kb_item["item"].get("Feature", [])).lower()
            q_txt = query_text.lower()
            
            # Simple Jaccard-ish overlap
            kb_tokens = set(kb_txt.split())
            q_tokens = set(q_txt.split())
            if not kb_tokens or not q_tokens:
                text_score = 0
            else:
                intersection = len(kb_tokens.intersection(q_tokens))
                union = len(kb_tokens.union(q_tokens))
                text_score = intersection / union if union > 0 else 0
            
            # 2. Audio Score
            audio_score = 0.0
            if query_audio_vector and kb_item["vector"]:
                # Ensure dimensions match roughly (truncate if needed)
                v1 = query_audio_vector
                v2 = kb_item["vector"]
                min_len = min(len(v1), len(v2))
                audio_score = cosine_similarity(v1[:min_len], v2[:min_len])
            
            # Fuse
            # If no audio provided, alpha effectively 0
            effective_alpha = alpha if query_audio_vector else 0.0
            final_score = (1 - effective_alpha) * text_score + effective_alpha * audio_score
            
            scores.append((final_score, kb_item["item"]))
        
        # Sort desc
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Return top-1 parameters
        if scores:
            return scores[0][1]['Parameters']
        return {}

if __name__ == "__main__":
    # Test
    dummy_vec = [0.1, 0.2, 0.3, 0.4, 0.5]
    dummy_data = [
        {"Style": ["Rock"], "Feature": ["Loud"], "Parameters": {"G": 1}, "Vector": "0.1, 0.2, 0.3, 0.4, 0.5"}, # Perfect audio match
        {"Style": ["Jazz"], "Feature": ["Smooth"], "Parameters": {"G": 2}, "Vector": "0.9, 0.0, 0.0, 0.0, 0.0"}
    ]
    
    rag = DualModalRAG(dummy_data)
    
    print("--- Test 1: Text Only (expect Jazz) ---")
    print(rag.retrieve("Smooth Jazz"))
    
    print("\n--- Test 2: Audio Dominated (expect Rock) ---")
    print(rag.retrieve("Smooth Jazz", query_audio_vector=dummy_vec, alpha=0.9))
