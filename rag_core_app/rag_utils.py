import os
import shutil
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import (
    PyMuPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader,
    CSVLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .models import ChatMessage

# === NEW IMPORTS ===
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# === HELPER: Get Unique Path per Session ===
def get_db_path(session_id):
    if not session_id:
        return None
    return f"faiss_indexes/session_{session_id}"

# === 1. DOCUMENT LOADING ===
def extract_text_with_ocr(file_path):
    try:
        # [FIX] Check if dependencies are actually callable
        import shutil
        if not shutil.which("tesseract"):
            print("Warning: Tesseract-OCR is not installed. Skipping OCR.")
            return ""
            
        poppler_path = os.getenv("POPPLER_PATH") 
        if poppler_path:
             images = convert_from_path(file_path, poppler_path=poppler_path)
        else:
             images = convert_from_path(file_path)
        
        full_text = ""
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"OCR Failed: {e}")
        return ""

def get_loader(file_path):
    """Factory function to get the correct loader based on extension"""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return PyMuPDFLoader(file_path)
    elif ext == ".txt":
        return TextLoader(file_path, encoding='utf-8')
    elif ext in [".docx", ".doc"]:
        return Docx2txtLoader(file_path)
    elif ext in [".pptx", ".ppt"]:
        return UnstructuredPowerPointLoader(file_path)
    elif ext in [".xlsx", ".xls"]:
        return UnstructuredExcelLoader(file_path)
    elif ext == ".csv":
        return CSVLoader(file_path)
    else:
        # Fallback for unknown text-based files (code, json, etc)
        return TextLoader(file_path, autodetect_encoding=True)

# === UPDATED PROCESS FILE ===
def process_file(file_path, session_id):
    if not session_id:
        print("Error: No session ID provided for processing.")
        return False

    db_path = get_db_path(session_id)
    print(f"Processing {file_path} for Session {session_id}...")
    
    documents = []
    try:
        loader = get_loader(file_path)
        documents = loader.load()
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return False

    # Check for empty content (e.g., Scanned PDFs)
    raw_text = "".join([doc.page_content for doc in documents])
    
    # OCR Fallback: Only run this for PDFs that came back empty
    if len(raw_text.strip()) < 50 and file_path.lower().endswith(".pdf"):
        print("Text too short. Attempting OCR...")
        ocr_text = extract_text_with_ocr(file_path)
        if ocr_text.strip():
            from langchain.schema import Document
            documents = [Document(page_content=ocr_text, metadata={"source": file_path})]
        else:
            return False

    # Split & Embed
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    
    if not docs:
        print("No content found to index.")
        return False

    return True

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    if os.path.exists(db_path):
        try:
            vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
            vector_store.add_documents(docs)
            vector_store.save_local(db_path)
        except:
            vector_store = FAISS.from_documents(docs, embeddings)
            vector_store.save_local(db_path)
    else:
        vector_store = FAISS.from_documents(docs, embeddings)
        vector_store.save_local(db_path)    

# === 2. SESSION-AWARE CHATBOT (Unchanged) ===
# Updated get_answer with Memory
def get_answer(query, session_id):
    db_path = get_db_path(session_id)
    
    # --- MEMORY UPGRADE: Fetch last 6 messages ---
    # We fetch them in reverse order (newest first) to get the latest, 
    # then reverse back to chronological order for the AI.
    recent_history = ChatMessage.objects.filter(session_id=session_id).order_by('-timestamp')[:6]
    history_text = "\n".join([f"{'User' if msg.is_user else 'AI'}: {msg.text}" for msg in reversed(recent_history)])

    try:
        llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant")
        
        # KEYWORDS for Web Search
        query_lower = query.lower()
        search_triggers = ["search", "find", "google", "online", "internet", "web", "price", "weather", "news"]

        # ROUTE 1: WEB SEARCH (with History)
        if any(keyword in query_lower for keyword in search_triggers):
            search = DuckDuckGoSearchRun()
            try:
                search_results = search.run(query)
                prompt = ChatPromptTemplate.from_template(
                    "Chat History:\n{history}\n\nSearch Results: {results}\nUser Question: {question}\nAnswer based on results and history."
                )
                chain = prompt | llm | StrOutputParser()
                return chain.invoke({"history": history_text, "results": search_results, "question": query})
            except:
                pass

        # ROUTE 2: DOCUMENT SEARCH (with History)
        if db_path and os.path.exists(db_path):
            embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            try:
                vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
                retriever = vector_store.as_retriever(search_kwargs={"k": 3})
                docs = retriever.invoke(query)
                
                if docs:
                    context_text = "\n\n".join([d.page_content for d in docs])
                    prompt = ChatPromptTemplate.from_template(
                        "Chat History:\n{history}\n\nContext from files:\n{context}\n\nQuestion: {question}\nAnswer based on context and history."
                    )
                    chain = prompt | llm | StrOutputParser()
                    return chain.invoke({"history": history_text, "context": context_text, "question": query})
            except Exception:
                pass 

        # ROUTE 3: GENERAL CHAT (with History)
        prompt = ChatPromptTemplate.from_template(
            "Chat History:\n{history}\n\nYou are a helpful assistant. User: {question}"
        )
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"history": history_text, "question": query})

    except Exception as e:
        return f"Error: {str(e)}"

# === 3. MEMORY MANAGEMENT (Unchanged) ===
def clear_data(session_id):
    db_path = get_db_path(session_id)
    if db_path and os.path.exists(db_path):
        try:
            shutil.rmtree(db_path)
        except Exception:
            pass

# === 4. TITLE GENERATOR (Unchanged) ===
def generate_chat_title(user_message, bot_response):
    try:
        llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant")
        prompt = f"Generate a short 3-5 word title for this chat.\nUser: {user_message}\nAI: {bot_response}"
        response = llm.invoke(prompt)
        return response.content.strip().replace('"', '')[:50]
    except:
        return user_message[:30]