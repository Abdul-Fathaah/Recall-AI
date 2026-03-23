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
from .models import ChatMessage
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# === GLOBAL MODEL LOADING ===
print("⏳ Loading Neural Core...")
try:
    GLOBAL_EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    CHAT_LLM = ChatGroq(temperature=0.6, model_name="llama-3.1-8b-instant", streaming=True)
    ROUTER_LLM = ChatGroq(temperature=0.0, model_name="llama-3.1-8b-instant")
    print("✅ Neural Core Online!")
except Exception as e:
    print(f"❌ Core Failure: {e}")
    GLOBAL_EMBEDDINGS = None
    CHAT_LLM = None
    ROUTER_LLM = None

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
        elif ext == ".pptx":
            try:
                from pptx import Presentation
                prs = Presentation(file_path)
                slides_text = []
                for i, slide in enumerate(prs.slides):
                    slide_content = []
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_content.append(shape.text.strip())
                    if slide_content:
                        slides_text.append(f"--- Slide {i+1} ---\n" + "\n".join(slide_content))
                full_text = "\n\n".join(slides_text)
                if full_text.strip():
                    return [Document(page_content=full_text, metadata={"source": file_path, "type": "pptx"})]
                return []
            except Exception as e:
                print(f"⚠️ PPTX load error: {e}")
                return []
        
        elif ext in [".xlsx", ".xls"]:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                all_rows = []
                for ws in wb.worksheets:
                    all_rows.append(f"--- Sheet: {ws.title} ---")
                    for row in ws.iter_rows(values_only=True):
                        cleaned = [str(cell) for cell in row if cell is not None]
                        if cleaned:
                            all_rows.append(" | ".join(cleaned))
                full_text = "\n".join(all_rows)
                if full_text.strip():
                    return [Document(page_content=full_text, metadata={"source": file_path, "type": "xlsx"})]
                return []
            except Exception as e:
                print(f"⚠️ XLSX load error: {e}")
                return []
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
            except Exception as e:
                print(f"⚠️ WARNING: FAISS index load failed for session {session_id}: {e}")
                print(f"⚠️ Rebuilding index from scratch — previously indexed content for this session is LOST.")
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
        search = DuckDuckGoSearchResults(num_results=4)
        print(f"🌎 Searching Web: {query}")
        return search.run(query)
    except Exception as e:
        return f"Web search failed: {e}"

def get_answer(query, session_id):
    db_path = get_db_path(session_id)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    recent_history = ChatMessage.objects.filter(session_id=session_id).order_by('-timestamp')[:6]
    history_text = "\n".join([f"{'User' if msg.is_user else 'AI'}: {msg.text}" for msg in reversed(recent_history)])

    chat_llm = CHAT_LLM
    router_llm = ROUTER_LLM

    # === STEP 0: INTENT CLASSIFICATION ===
    try:
        router_prompt = ChatPromptTemplate.from_template(
            "Classify the following user input: '{question}'.\n"
            "If the user is asking for ANY real-world facts, current events, knowledge, programming help, or specific information, reply ONLY with 'QUERY'.\n"
            "If the user is ONLY making small talk, greeting you, or saying thanks, reply ONLY with 'CHAT'."
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
    use_web = False
    
    if db_path and os.path.exists(db_path) and GLOBAL_EMBEDDINGS:
        try:
            vector_store = FAISS.load_local(db_path, GLOBAL_EMBEDDINGS, allow_dangerous_deserialization=True)
            docs_with_scores = vector_store.similarity_search_with_score(query, k=5)
            if docs_with_scores:
                top_score = docs_with_scores[0][1]
                docs = [d for d, _ in docs_with_scores]
                context_text = "\n\n".join([d.page_content for d in docs])
                use_web = top_score > 0.85
            else:
                use_web = True
        except Exception as e:
            print(f"⚠️ Retrieval error: {e}")
            use_web = True
    else:
        use_web = True

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
    1. Answer accurately using the context provided.
    2. If context is from Web, synthesize the facts and use the provided snippets to give a comprehensive answer, including Markdown links `[Source Name](URL)` to the sources at the end.
    3. If context is from Knowledge Base, cite documents.
    4. Be helpful, professional, and detailed.
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