import os
import shutil
import pytesseract
import requests
import concurrent.futures
from io import BytesIO
from datetime import datetime
from PIL import Image
from pdf2image import convert_from_path
from langchain_community.document_loaders import (
    PyMuPDFLoader, 
    TextLoader, 
    Docx2txtLoader, 
    CSVLoader,
    WebBaseLoader
)
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .models import ChatMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# === GLOBAL MODEL LOADING ===
print("⏳ Loading Neural Core...")
try:
    GLOBAL_EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print("✅ Neural Core Online!")
except Exception as e:
    print(f"❌ Core Failure: {e}")
    GLOBAL_EMBEDDINGS = None

def get_db_path(session_id):
    if not session_id: return None
    return f"faiss_indexes/session_{session_id}"

# =========================================================
#  1. OPTIMIZED BULK INGESTION (Image & URL Support)
# =========================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_single_file(file_path):
    """
    Universal Loader: Handles URLs (Images/Websites) and Local Files (Docs/Images).
    """
    try:
        # --- CASE A: WEB URLS ---
        if file_path.startswith("http://") or file_path.startswith("https://"):
            print(f"🌐 Analyzing URL: {file_path}")
            
            # Check if URL is an image
            if any(file_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                print("📷 Remote Image Detected. Downloading & OCR...")
                try:
                    response = requests.get(file_path, headers=HEADERS, timeout=10)
                    image = Image.open(BytesIO(response.content))
                    text = pytesseract.image_to_string(image)
                    if text.strip():
                        return [Document(page_content=text, metadata={"source": file_path, "type": "image_url"})]
                    return []
                except Exception as e:
                    print(f"❌ Failed to process remote image: {e}")
                    return []
            
            # Treat as Standard Website
            try:
                loader = WebBaseLoader(file_path, header_template=HEADERS)
                return loader.load()
            except Exception as e:
                print(f"❌ Web Load Error: {e}")
                return []

        # --- CASE B: LOCAL FILES ---
        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. Local Images
        if ext in ['.png', '.jpg', '.jpeg']:
            print(f"📷 Local Image Detected: {file_path}")
            try:
                text = pytesseract.image_to_string(Image.open(file_path))
                if text.strip():
                    return [Document(page_content=text, metadata={"source": file_path})]
                return []
            except Exception as e:
                print(f"OCR Error: {e}")
                return []

        # 2. Local Documents
        if ext == ".pdf": return PyMuPDFLoader(file_path).load()
        elif ext == ".txt": return TextLoader(file_path, encoding='utf-8').load()
        elif ext in [".docx", ".doc"]: return Docx2txtLoader(file_path).load()
        elif ext == ".csv": return CSVLoader(file_path).load()
        else: return TextLoader(file_path, autodetect_encoding=True).load()

    except Exception as e:
        print(f"⚠️ Failed to load {file_path}: {e}")
        return []

def process_files_bulk(file_paths, session_id):
    """
    Parallel processing for Files, URLs, and Images.
    """
    if not session_id or not GLOBAL_EMBEDDINGS or not file_paths:
        return False
        
    db_path = get_db_path(session_id)
    all_documents = []

    # Parallel Execution
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(load_single_file, file_paths)
        for res in results:
            if res: all_documents.extend(res)

    if not all_documents:
        return False

    # Split & Index
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(all_documents)
    
    if not docs:
        return False

    try:
        if os.path.exists(db_path):
            try:
                vector_store = FAISS.load_local(db_path, GLOBAL_EMBEDDINGS, allow_dangerous_deserialization=True)
                vector_store.add_documents(docs)
                vector_store.save_local(db_path)
            except:
                vector_store = FAISS.from_documents(docs, GLOBAL_EMBEDDINGS)
                vector_store.save_local(db_path)
        else:
            vector_store = FAISS.from_documents(docs, GLOBAL_EMBEDDINGS)
            vector_store.save_local(db_path)
        return True
    except Exception as e:
        print(f"❌ Indexing Failed: {e}")
        return False

def process_file(file_path, session_id):
    """Legacy wrapper for backward compatibility."""
    return process_files_bulk([file_path], session_id)

# =========================================================
#  2. STREAMING GENERATION ENGINE
# =========================================================

def perform_web_search(query):
    try:
        search = DuckDuckGoSearchRun()
        print(f"🌎 Searching Web: {query}")
        return search.run(query)
    except Exception as e:
        return f"Web search failed: {e}"

def get_answer(query, session_id):
    db_path = get_db_path(session_id)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    recent_history = ChatMessage.objects.filter(session_id=session_id).order_by('-timestamp')[:6]
    history_text = "\n".join([f"{'User' if msg.is_user else 'AI'}: {msg.text}" for msg in reversed(recent_history)])

    chat_llm = ChatGroq(temperature=0.6, model_name="llama-3.1-8b-instant", streaming=True)
    router_llm = ChatGroq(temperature=0.0, model_name="llama-3.1-8b-instant")

    # === STEP 0: INTENT CLASSIFICATION ===
    try:
        router_prompt = ChatPromptTemplate.from_template(
            "Classify: '{question}'. Reply ONLY 'CHAT' (small talk) or 'QUERY' (info request)."
        )
        intent = (router_prompt | router_llm | StrOutputParser()).invoke({"question": query}).strip().upper()
    except:
        intent = "QUERY"

    print(f"🧠 Intent Detected: {intent}")

    # === PATH A: CASUAL CHAT ===
    if "CHAT" in intent:
        prompt = ChatPromptTemplate.from_template(
            """
            You are a witty, intelligent AI assistant.
            History: {history}
            User: {question}
            Reply naturally and helpfully.
            """
        )
        chain = prompt | chat_llm | StrOutputParser()
        for chunk in chain.stream({"history": history_text, "question": query}):
            yield chunk
        return

    # === PATH B: KNOWLEDGE QUERY ===
    context_text = ""
    source_type = "Knowledge Base"
    
    if db_path and os.path.exists(db_path) and GLOBAL_EMBEDDINGS:
        try:
            vector_store = FAISS.load_local(db_path, GLOBAL_EMBEDDINGS, allow_dangerous_deserialization=True)
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            docs = retriever.invoke(query)
            if docs:
                context_text = "\n\n".join([d.page_content for d in docs])
        except Exception as e:
            print(f"⚠️ Retrieval error: {e}")

    # Fallback to Web
    use_web = False
    if not context_text:
        use_web = True
    else:
        check_prompt = ChatPromptTemplate.from_template(
            "Query: {q}. Context: {c}. Does context contain answer? Reply YES or NO."
        )
        try:
            grade = (check_prompt | router_llm | StrOutputParser()).invoke({"q": query, "c": context_text[:2000]}).strip().upper()
            if "NO" in grade: use_web = True
        except: pass

    if use_web:
        print("⚠️ Docs irrelevant or empty. Switching to Web Search.")
        source_type = "Web Search"
        context_text = perform_web_search(query)

    # Final Generation
    system_prompt = """
    You are a highly capable AI assistant.
    Current Date: {date}
    
    Context ({source}):
    {context}
    
    User Question: {question}
    
    Instructions:
    1. Answer accurately using the context.
    2. If context is from Web, synthesize facts.
    3. If context is from Knowledge Base, cite documents.
    4. Be helpful and professional.
    """
    
    final_prompt = ChatPromptTemplate.from_template(system_prompt)
    chain = final_prompt | chat_llm | StrOutputParser()
    
    for chunk in chain.stream({
        "date": current_date,
        "source": source_type,
        "context": context_text,
        "question": query
    }):
        yield chunk

# === UTILITIES ===
def clear_data(session_id):
    db_path = get_db_path(session_id)
    if db_path and os.path.exists(db_path):
        try: shutil.rmtree(db_path)
        except: pass

def generate_chat_title(user_message, bot_response):
    try:
        llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant")
        prompt = f"Summarize into a 4-word title:\nUser: {user_message}\nAI: {bot_response}"
        return llm.invoke(prompt).content.strip().replace('"', '')[:50]
    except:
        return user_message[:30]