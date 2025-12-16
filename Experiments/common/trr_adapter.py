import os
import torch
import numpy as np
from typing import List, Dict, Any, Optional

# Import TRR components
try:
    from Experiments.TextureResonance.texture_encoder import TextureEncoder, similarity_score, SourcePurifier
except ImportError:
    # Handle relative import if needed
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from Experiments.TextureResonance.texture_encoder import TextureEncoder, similarity_score, SourcePurifier

class TRRRetriever:
    """
    Adapter for Texture Resonance Retrieval.
    Compatible with the run_ablation.py interface.
    """
    def __init__(self, dataset: List[Dict[str, Any]]):
        self.encoder = TextureEncoder(project_dim=64)
        self.dataset = dataset
        self.embeddings = []
        self.metadata = []
        
        print("Initializing TRRRetriever...")
        self._index_dataset()
        
    def _index_dataset(self):
        """Pre-computes embeddings for all items in dataset with valid AudioPath."""
        success_count = 0
        for item in self.dataset:
            audio_path = item.get('AudioPath')
            embedding = None
            
            if audio_path and os.path.exists(audio_path):
                # Try to use cached embedding if we decide to save them, 
                # but for now we compute on fly or assume pre-computed.
                # Re-computing on initialization might be slow.
                # Implementation Decision: For ablation size (small), okay to compute?
                # Actually, TRR is heavy. Ideally we cache.
                # For this demo adapter, we will compute.
                
                # Check for cached .npy
                cache_path = audio_path + ".trr.npy"
                if os.path.exists(cache_path):
                    embedding = np.load(cache_path)
                else:
                    try:
                        embedding = self.encoder.get_embedding(audio_path)
                        if embedding is not None:
                            np.save(cache_path, embedding)
                    except Exception as e:
                        print(f"TRR Error {audio_path}: {e}")

            if embedding is not None:
                self.embeddings.append(embedding)
                self.metadata.append(item)
                success_count += 1
            else:
                # Keep index alignment? No, we filter. Retrieval will be smaller subset?
                # Or we can insert zero-vector to keep alignment with dataset indices (if id-based).
                # run_ablation refers to Ground Truth Params by ID? No, it passes query.
                pass
                
        self.embeddings = np.array(self.embeddings) if self.embeddings else np.empty((0, 4096))
        print(f"TRR Indexed {success_count}/{len(self.dataset)} items with audio.")

    def retrieve_top_k(self, query_text: str, query_audio_path: Optional[str] = None, alpha: float = 0.5, k: int = 5):
        """
        Retrieves top K items.
        Note: TRR is PURE Audio (Texture). It ignores query_text unless we hybridize.
        Experiment 4 is 'Texture vs Vector', so we assume it's Audio-Only comparison for now,
        or we can mix it.
        
        Args:
            query_text: Ignored (or used for hybrid future)
            query_audio_path: Path to query audio file.
            alpha: Ignored for pure TRR.
            k: Number of results.
        """
        if query_audio_path is None or not os.path.exists(query_audio_path):
            print("TRR: No valid query audio path provided.")
            return []

        # 1. Compute Query Embedding
        query_emb = self.encoder.get_embedding(query_audio_path)
        if query_emb is None:
            return []
            
        # 2. Cosine Similarity
        if len(self.embeddings) == 0:
            return []
            
        scores = np.dot(self.embeddings, query_emb)
        
        # 3. Rank
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            meta = self.metadata[idx]
            results.append({
                "params": meta['Parameters'],
                "score": score,
                "song_name": meta['SongName'],
                "type": "texture_match"
            })
            
        return results
