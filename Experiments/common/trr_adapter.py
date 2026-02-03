import os
import torch
import numpy as np
from typing import List, Dict, Any, Optional

class TRRRetriever:
    """
    Adapter for Texture Resonance Retrieval.
    Compatible with the run_ablation.py interface.
    OPTIMIZED: Lazy loads model only if cache is missing.
    """
    def __init__(self, dataset: List[Dict[str, Any]]):
        self.encoder = None # Lazy load
        self.dataset = dataset
        self.embeddings = []
        self.metadata = []
        
        print("Initializing TRRRetriever (Cache Optimized)...")
        self._index_dataset()
        
    def _get_encoder(self):
        """Lazy load the encoder"""
        if self.encoder is None:
            print("[TRR] Loading TextureEncoder Model (Cache Miss)...")
            try:
                from Experiments.TextureResonance.texture_encoder import TextureEncoder
                self.encoder = TextureEncoder(project_dim=64)
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
                from Experiments.TextureResonance.texture_encoder import TextureEncoder
                self.encoder = TextureEncoder(project_dim=64)
        return self.encoder

    def _index_dataset(self):
        """Pre-computes embeddings for all items in dataset with valid AudioPath."""
        success_count = 0
        for item in self.dataset:
            audio_path = item.get('AudioPath')
            embedding = None
            
            # 1. Try JSON Cache (Unified Dataset)
            if 'Vectors' in item and item['Vectors'].get('TRR'):
                embedding = np.array(item['Vectors']['TRR'])
            
            # 2. Try File Cache
            elif audio_path and os.path.exists(audio_path):
                # 1. Try Cache First
                cache_path = audio_path + ".trr.npy"
                if os.path.exists(cache_path):
                    try:
                        embedding = np.load(cache_path)
                    except: pass
                
                # 2. Compute if missing
                if embedding is None:
                    try:
                        encoder = self._get_encoder()
                        embedding = encoder.get_embedding(audio_path)
                        # Avoid saving during experiment run if using JSON source primarily
                    except Exception as e:
                        print(f"TRR Error {audio_path}: {e}")

            if embedding is not None:
                self.embeddings.append(embedding)
                self.metadata.append(item)
                success_count += 1
                
        self.embeddings = np.array(self.embeddings) if self.embeddings else np.empty((0, 4096))
        print(f"TRR Indexed {success_count}/{len(self.dataset)} items with audio.")

    def retrieve_top_k(self, query_text: str, query_audio_path: Optional[str] = None, query_vector: Optional[List[float]] = None, alpha: float = 0.5, k: int = 5):
        """
        Retrieves top K items.
        OPTIMIZED: Checks query cache first. Supports direct vector input.
        """
        query_emb = None
        
        # 1. Use Direct Vector if provided
        if query_vector is not None:
             query_emb = np.array(query_vector)
             
        # 2. Use Audio Path (Compute or Cache)
        elif query_audio_path and os.path.exists(query_audio_path):
            cache_path = query_audio_path + ".trr.npy"
            if os.path.exists(cache_path):
                try:
                    query_emb = np.load(cache_path)
                    # print(f"DEBUG: TRR Query Cache Hit: {cache_path}")
                except: pass
                
            if query_emb is None:
                encoder = self._get_encoder()
                query_emb = encoder.get_embedding(query_audio_path)
        else:
             print("TRR: No valid query audio path or vector provided.")
             return []
            
        if query_emb is None:
            return []
            
        # 2. Cosine Similarity (normalized)
        if len(self.embeddings) == 0:
            return []
        
        # Normalize query embedding
        query_norm = np.linalg.norm(query_emb)
        if query_norm == 0:
            return []
        query_emb_normalized = query_emb / query_norm
        
        # Normalize all embeddings and compute cosine similarity
        emb_norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        emb_norms[emb_norms == 0] = 1  # Avoid division by zero
        embeddings_normalized = self.embeddings / emb_norms
        
        scores = np.dot(embeddings_normalized, query_emb_normalized)
        
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
