import os
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChatBot.settings')
import django
django.setup()

from rag_core_app.rag_utils import get_llm, get_answer
from langchain.docstore.document import Document

def test_token_limit():
    print("--- Testing Token/Context Limits ---")
    
    # 1. Simulate a VERY long context (similar to what we just configured: 4 chunks * 800 chars = 3200 chars)
    # flan-t5 usually has a 512 token limit. 3200 chars is roughly 800 tokens.
    # This should likely cause truncation or failure.
    
    long_text = "This is a test sentence repeated to fill space. " * 100 # ~4800 chars
    
    print(f"Generated text of length: {len(long_text)}")
    
    query = "What is the summary?"
    
    # We will try to invoke the LLM directory first to see if it crashes on length
    try:
        llm = get_llm()
        print("Invoking LLM with long prompt...")
        # Simulating what the chain does roughly
        prompt = f"Context: {long_text}\n\nQuestion: {query}"
        response = llm.invoke(prompt)
        print(f"LLM Response (Direct): {response}")
    except Exception as e:
        print(f"LLM Direct Invocation Failed: {e}")

    # Now test the full chain if possible (need to mock vector store or just trust the direct test)
    # The chain adds even more overhead.
    
if __name__ == "__main__":
    test_token_limit()
