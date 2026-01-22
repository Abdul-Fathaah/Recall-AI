import os
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# =============== CONFIGURATION =================
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DB_PATH = "faiss_index"
# =================================================

# === 1. ROBUST LOADER (OCR) ===
def extract_text_with_ocr(file_path):
    """
    Fallback method: Converts PDF pages to images and reads text using Tesseract.
    """
    poppler_path = os.getenv("POPPLER_PATH")

    # Check if path exists or if it's None (for Linux/Mac where it might be in PATH automatically)
    if poppler_path:
        images = convert_from_path(file_path, poppler_path=poppler_path)
    else:
        # Fallback for systems where poppler is in the system PATH
        images = convert_from_path(file_path)
    try:
        print("Attempting OCR (this might take a while)...")
        # You might need to specify the poppler_path here if on Windows 
        full_text = ""
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"OCR Failed: {e}")
        return ""

def process_file(file_path):
    print(f"Processing {file_path}...")
    documents = []
    
    # 1. Try Standard Loaders first
    try:
        if file_path.endswith(".txt"):
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
        else:
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
    except Exception:
        pass

    # 2. Check Quality - If empty/garbage, use OCR
    raw_text = "".join([doc.page_content for doc in documents])
    if len(raw_text.strip()) < 50: 
        print("Standard read failed. Switching to OCR...")
        ocr_text = extract_text_with_ocr(file_path)
        if ocr_text.strip():
            # Create a manual document object since OCR returns raw string
            from langchain.schema import Document
            documents = [Document(page_content=ocr_text, metadata={"source": file_path})]
        else:
            print("OCR also failed or file is empty.")
            return

    # 3. Vectorize
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # === NEW LOGIC: APPEND INSTEAD OF OVERWRITE ===
    if os.path.exists(DB_PATH):
        print("Existing knowledge base found. Merging new data...")
        try:
            # 1. Load existing index
            vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
            # 2. Add new documents to it
            vector_store.add_documents(docs)
            # 3. Save the updated index
            vector_store.save_local(DB_PATH)
            print("Success! The brain has been expanded (merged).")
        except Exception as e:
            print(f"Error merging into existing index: {e}")
            print("Falling back to creating a new index...")
            vector_store = FAISS.from_documents(docs, embeddings)
            vector_store.save_local(DB_PATH)
    else:
        print("No existing knowledge base. Creating new one...")
        vector_store = FAISS.from_documents(docs, embeddings)
        vector_store.save_local(DB_PATH)    

def get_answer(query):
    # 1. Load the Memory
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    try:
        vector_store = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    except:
        return "I am empty! Please upload a document first."

    try:
        llm = ChatGroq(
            temperature=0.3, 
            model_name="llama-3.1-8b-instant"
        )
    except Exception as e:
        return f"Error connecting to Groq: {e}"
    
    # 3. Create the Prompt
    template = """You are an intelligent personal assistant (Personal Gemini). 
    Your goal is to explain the answer clearly and structurally based on the context provided.
    
    Guidelines:
    1. Use **bold text** for key terms or headings.
    2. Use bullet points or numbered lists for steps and details.
    3. If the context doesn't contain the answer, say "I couldn't find that in your documents."
    4. Keep the tone professional but friendly.

    Context: {context}
    
    Question: {question}
    
    Answer:"""
    
    QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

    # 4. Run the Chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, 
        chain_type="stuff", 
        retriever=vector_store.as_retriever(),
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
    )
    
    try:
        return qa_chain.invoke(query)['result']
    except Exception as e:
        return f"Error: {str(e)}"