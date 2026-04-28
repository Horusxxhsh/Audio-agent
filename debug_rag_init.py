import os
import sys

# Add common directory
common_dir = os.path.join(os.path.dirname(__file__), 'Experiments', 'common')
sys.path.append(common_dir)

from dataset_loader import load_and_merge_data
from rag_adapter import RAGRetriever 

print("Loading Data...")
data = load_and_merge_data()
kb_set = data[:10]
print(f"KB Set size: {len(kb_set)}")

print("Initializing RAG...")
try:
    rag = RAGRetriever(kb_set)
    print("Success!")
    rag.cleanup()
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
