import sys
import os
import shutil
import tempfile
import json
from typing import List, Dict, Any

# Add Source directory to path to import rag_system
current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.join(current_dir, '..', '..', 'Source')
sys.path.append(source_dir)

try:
    from rag_system import AudioRAGSystem
    import chromadb.utils.embedding_functions as embedding_functions
    
    # PATCH: Override SentenceTransformer to avoid downloading model from HF (Network Timeout)
    class DummyEmbeddingFunction:
        def __init__(self, model_name=None):
            import numpy as np
            np.random.seed(42)  # 固定种子确保可复现

        def __call__(self, input: List[str]) -> List[List[float]]:
             import numpy as np
             if isinstance(input, str): input = [input]
             return [np.random.rand(384).tolist() for _ in input]

        def embed_query(self, *args, **kwargs) -> List[float]:
            import numpy as np
            return np.random.rand(384).tolist()

        def embed_documents(self, *args, **kwargs) -> List[List[float]]:
            return self.__call__(kwargs.get('input', args[0] if args else []))
             
    # Monkey patch the function in the module
    embedding_functions.SentenceTransformerEmbeddingFunction = DummyEmbeddingFunction

except ImportError:
    print("Error: Could not import AudioRAGSystem from Source. Make sure requirements are installed.")
    AudioRAGSystem = None

class RAGRetriever:
    """
    Adapter class to use AudioRAGSystem in experiments.
    Creates a TEMPORARY ChromaDB instance to identify knowledge base from training data
    without polluting the main user database.
    """
    def __init__(self, training_data: List[Dict]):
        # Always store data for text retrieval.
        self.training_data = training_data

        # If the full RAG stack isn't available (e.g., chromadb not installed),
        # we still support a deterministic keyword-overlap text retriever so
        # objective experiments can run offline.
        self.rag = None
        self.temp_dir = None
        if not AudioRAGSystem:
            print("[RAGRetriever] AudioRAGSystem unavailable; falling back to simple text retrieval only.")
            return

        # Create a temporary directory for the vector DB
        self.temp_dir = tempfile.mkdtemp(prefix="audio_agent_experiment_")
        print(f"[RAGRetriever] Initializing temporary RAG DB at: {self.temp_dir}")

        # Initialize RAG System with temp dir
        # Priority: DEEPSEEK_API_KEY -> OPENAI_API_KEY (no hardcoded secrets)
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.deepseek.com"
        if not api_key:
            print("[RAGRetriever] Missing API key (DEEPSEEK_API_KEY / OPENAI_API_KEY); falling back to simple text retrieval only.")
            return
        
        self.rag = AudioRAGSystem(
            api_key=api_key,
            persist_directory=self.temp_dir,
            base_url=base_url,
        )

        # Populate DB with training data
        self._populate_db(training_data)

    def _populate_db(self, data: List[Dict]):
        print(f"[RAGRetriever] Populating DB with {len(data)} items...")
        for item in data:
            # We treat each dataset item as a "Parameter Preset"
            song_name = item.get('SongName', 'Unknown')
            params = item.get('Parameters', {})
            style = item.get('Style', [])
            feature = item.get('Feature', [])
            
            # Combine features into a description string
            description = ", ".join(feature) if feature else f"Style: {', '.join(style)}"
            
            # Add to RAG
            # Add to RAG
            # Load Vector from .npy cache if available (User request: DB vector is bad)
            raw_vector = item.get('Vector')
            audio_path = item.get('AudioPath')
            vector = []

            # 1. Try Loading from JSON Cache (Unified Dataset)
            # Schema: item['Vectors']['Wav2Vec']
            if 'Vectors' in item and item['Vectors'].get('Wav2Vec'):
                vec_data = item['Vectors']['Wav2Vec']
                # FIX: Check if vector has content (not empty list)
                # Empty list [] should NOT be used as audio vector
                if len(vec_data) > 0 and vec_data[0] is not None:
                    vector = vec_data
                # else: vector remains [] (empty) which won't be added to audio_collection
            
            # 2. Fallback to .npy (Legacy)
            elif audio_path and os.path.exists(audio_path + ".wav2vec.npy"):
                 try:
                     import numpy as np
                     vector = np.load(audio_path + ".wav2vec.npy").tolist()
                 except: pass

            # 3. Fallback to DB vector string
            if not vector and raw_vector:
                if isinstance(raw_vector, str):
                    try: vector = [float(x) for x in raw_vector.split(',')]
                    except: pass
                elif isinstance(raw_vector, list):
                    try: vector = [float(x) for x in raw_vector]
                    except: pass
            
            self.rag.add_parameter_preset(
                preset_name=song_name,
                parameters=params,
                style_tags=style,
                description=description,
                user_rating="accept", # Assume training data is "good"
                audio_vector=vector
            )
            
    def retrieve_top_k(self, query_text: str, query_audio_vector=None, alpha=0.5, k=3):
        """
        Interprets the query for RAG and returns top-k items in the expected format.
        Uses simple keyword matching for Text to avoid Dummy Embedding randomness.
        """
        
        # 1. Pure Text Retrieval (Simple Keyword Match)
        if query_audio_vector is None:
            print(f"[RAGRetriever] Doing Simple Text Search for: {query_text[:50]}...")
            scores = []
            query_words = set(query_text.lower().split())
            
            for item in self.training_data:
                # Construct document text from item fields
                # SongName is weighted heavily if it appears in query
                name = item.get('SongName', '').lower()
                style = " ".join(item.get('Style', [])).lower()
                desc = " ".join(item.get('Feature', [])).lower()
                full_text = f"{name} {style} {desc}"
                
                # Simple score: overlap count
                # Bonus for exact name match
                score = 0
                if name and name in query_text.lower():
                    score += 10.0 # High relevance if name is explicitly queried
                
                # Word overlap
                doc_words = set(full_text.split())
                overlap = len(query_words.intersection(doc_words))
                score += overlap
                
                scores.append((score, item))
            
            # Sort by score desc
            scores.sort(key=lambda x: x[0], reverse=True)
            top_items = [x[1] for x in scores[:k]]
            
            # Convert to expected format (deep copy to avoid mutation)
            import copy
            return copy.deepcopy(top_items)

        # 2. Audio/Hybrid Retrieval (Use RAG System with Real Vectors)
        if self.rag is None:
            # Offline fallback: return empty to make the limitation explicit.
            # (Most experiment scripts use this adapter only for text-only retrieval.)
            return []

        results = self.rag.retrieve_similar_knowledge(
            query=query_text,
            n_results=k,
            collection_type="parameter",
            audio_query_vector=query_audio_vector,
            weight_audio=alpha
        )
        
        # Convert back to dataset format
        retrieved_items = []
        for res in results:
            metadata = res.get('metadata', {})
            item = {
                "SongName": metadata.get('preset_name'),
                "Parameters": json.loads(metadata.get('parameters', '{}')),
                "Style": json.loads(metadata.get('style_tags', '[]')),
                "Feature": [metadata.get('description', '')], 
                "Vector": None 
            }
            retrieved_items.append(item)
            
        return retrieved_items

    def cleanup(self):
        """Clean up temporary directory"""
        if not self.temp_dir:
            return

        try:
            # Close client if possible? Chroma 0.4+ usually handles via GC but good to be safe if specific close exists
            pass
        except Exception:
            pass

        if os.path.exists(self.temp_dir):
            print(f"[RAGRetriever] Cleaning up temp dir: {self.temp_dir}")
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp dir: {e}")

    def __del__(self):
        self.cleanup()
