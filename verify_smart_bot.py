import os
import sys
import shutil

# Setup paths
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChatBot.settings')
import django
django.setup()

from rag_core_app.rag_utils import get_answer, process_file

def test_conversation():
    print("--- Testing Smart Bot Conversation ---")
    
    # Force rebuild of index to ensure we test the new chunk settings
    print("Forcing index rebuild...")
    if os.path.exists("faiss_index"):
        shutil.rmtree("faiss_index")
        
    # Create a dummy PDF
    import fitz
    if not os.path.exists("test_rebuild.pdf"):
        doc = fitz.open()
        page = doc.new_page()
        text = """
        Artificial Intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems.
        These processes include learning (the acquisition of information and rules for using the information), reasoning (using rules to reach approximate or definite conclusions), and self-correction.
        Particular applications of AI include expert systems, speech recognition and machine vision.
        
        Machine Learning is a subset of AI. It focuses on the use of data and algorithms to imitate the way that humans learn, gradually improving its accuracy.
        """
        page.insert_text((50, 50), text)
        doc.save("test_rebuild.pdf")
        doc.close()
    
    process_file("test_rebuild.pdf")
    
    # Now test conversation
    history = []
    
    # 1. First Question
    q1 = "What is the main topic of the uploaded document?"
    print(f"\nUser: {q1}")
    a1 = get_answer(q1, chat_history=history)
    print(f"Bot: {a1}")
    
    history.append((q1, a1))
    
    # 2. Check for Token Limit Crash (The real test!)
    # We ask a question that might pull multiple chunks if not careful
    q2 = "Explain the relationship between specific applications mentioned."
    print(f"\nUser: {q2}")
    a2 = get_answer(q2, chat_history=history)
    print(f"Bot: {a2}")

    if "indexing errors" in str(a2) or "Error" in str(a2) or len(a2) < 5:
        print("\nFAILURE: Limits likely exceeded or error occurred.")
    else:
        print("\nSUCCESS: Bot responded without crashing.")

if __name__ == "__main__":
    test_conversation()
