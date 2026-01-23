import os
import shutil
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from dotenv import load_dotenv

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

# === UPDATED PROCESS FILE: Accepts session_id ===
def process_file(file_path, session_id):
    if not session_id:
        print("Error: No session ID provided for processing.")
        return

    db_path = get_db_path(session_id)
    print(f"Processing {file_path} for Session {session_id}...")
    
    documents = []
    try:
        if file_path.endswith(".txt"):
            loader = TextLoader(file_path, encoding='utf-8')
            documents = loader.load()
        else:
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
    except Exception:
        pass

    raw_text = "".join([doc.page_content for doc in documents])
    if len(raw_text.strip()) < 50: 
        ocr_text = extract_text_with_ocr(file_path)
        if ocr_text.strip():
            from langchain.schema import Document
            documents = [Document(page_content=ocr_text, metadata={"source": file_path})]
        else:
            return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
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

# === 2. SESSION-AWARE CHATBOT ===
def get_answer(query, session_id):
    db_path = get_db_path(session_id)
    
    try:
        llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant")
        
        # KEYWORDS
        query_lower = query.lower()
        search_triggers = ["search", "find", "google", "online", "internet", "web", "price", "weather", "news"]

        # ROUTE 1: WEB SEARCH
        if any(keyword in query_lower for keyword in search_triggers):
            search = DuckDuckGoSearchRun()
            try:
                search_results = search.run(query)
                prompt = ChatPromptTemplate.from_template("Search Results: {results}\nUser Question: {question}\nAnswer based on results.")
                chain = prompt | llm | StrOutputParser()
                return chain.invoke({"results": search_results, "question": query})
            except:
                pass

        # ROUTE 2: DOCUMENT SEARCH (Specific to this Session)
        if db_path and os.path.exists(db_path):
            embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            try:
                vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
                retriever = vector_store.as_retriever(search_kwargs={"k": 3})
                docs = retriever.invoke(query)
                
                if docs:
                    context_text = "\n\n".join([d.page_content for d in docs])
                    prompt = ChatPromptTemplate.from_template("Context from files:\n{context}\n\nQuestion: {question}\nAnswer based on context.")
                    chain = prompt | llm | StrOutputParser()
                    return chain.invoke({"context": context_text, "question": query})
            except Exception:
                pass 

        # ROUTE 3: GENERAL CHAT
        prompt = ChatPromptTemplate.from_template("You are a helpful assistant. User: {question}")
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"question": query})

    except Exception as e:
        return f"Error: {str(e)}"

# === 3. MEMORY MANAGEMENT ===
def clear_data(session_id):
    """Deletes the specific folder for this session."""
    db_path = get_db_path(session_id)
    if db_path and os.path.exists(db_path):
        try:
            shutil.rmtree(db_path)
        except Exception:
            pass

# === 4. TITLE GENERATOR ===
def generate_chat_title(user_message, bot_response):
    try:
        llm = ChatGroq(temperature=0.3, model_name="llama-3.1-8b-instant")
        prompt = f"Generate a short 3-5 word title for this chat.\nUser: {user_message}\nAI: {bot_response}"
        response = llm.invoke(prompt)
        return response.content.strip().replace('"', '')[:50]
    except:
        return user_message[:30]