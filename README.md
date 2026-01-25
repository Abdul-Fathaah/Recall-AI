# RecallAI - Personalized RAG Chatbot

**RecallAI** is a powerful, Django-based AI assistant that uses **Retrieval-Augmented Generation (RAG)** to allow users to upload documents (PDFs, text files) and chat with them intelligently. It features a modern **Liquid Glassmorphism UI**, persistent chat history, and session-based memory using **FAISS** and **Groq's Llama 3**.

## 🚀 Features

* **📄 Document Q&A**: Upload multiple PDF or TXT files and ask questions based on their content.
* **🧠 Advanced RAG Engine**: Uses **LangChain** and **FAISS** vector stores to retrieve relevant context for every query.
* **⚡ Fast Inference**: Powered by **Groq API** (Llama-3.1-8b-instant) for lightning-fast responses.
* **👁️ OCR Capabilities**: Integrated **Tesseract OCR** & **pdf2image** to extract text from scanned documents or images.
* **💾 Persistent Sessions**: Chat history is saved in a MySQL database. Create multiple "Chat Sessions," each with its own isolated document context.
* **🎨 Modern UI**: A sleek, fully responsive **Liquid Glassmorphism** interface designed with deep gradients and frosted glass effects.
* **🔐 User Authentication**: Secure Login/Register system to keep user data private.

## 🛠️ Tech Stack

* **Backend:** Django 4.x, Python 3.10+
* **AI/ML:** LangChain, FAISS (Vector Store), Groq API (LLM)
* **Database:** MySQL (Production-ready data persistence)
* **Frontend:** HTML5, CSS3 (Custom Glassmorphism), Vanilla JavaScript
* **Utilities:** Pytesseract (OCR), Poppler (PDF processing)

## 📋 Prerequisites

Before running the project, ensure you have the following installed:

1.  **Python 3.8+**
2.  **MySQL Server**
3.  **Tesseract-OCR** (Required for processing images/scanned PDFs)
    * *Windows:* [Download Installer](https://github.com/UB-Mannheim/tesseract/wiki)
    * *Linux:* `sudo apt-get install tesseract-ocr`
    * *Mac:* `brew install tesseract`
4.  **Poppler** (Required for `pdf2image`)
    * *Windows:* [Download Binary](https://github.com/oschwartz10612/poppler-windows/releases/) and add to PATH.
    * *Linux:* `sudo apt-get install poppler-utils`
    * *Mac:* `brew install poppler`

## ⚙️ Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/recallai-chatbot.git](https://github.com/yourusername/recallai-chatbot.git)
cd recallai-chatbot
```
### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
Note: If requirements.txt is missing, install the core packages: 

```bash
pip install django mysqlclient langchain langchain-community langchain-groq faiss-cpu
pip install python-dotenv
pip install pdf2image pytesseract
```

### 4. Configure Environment Variables
Create a .env file in the root directory and add the following:

```Code snippet
# Django Settings
DEBUG=True
DJANGO_SECRET_KEY=your_django_secret_key_here

# Database (MySQL)
DB_NAME=recallai_db
DB_USER=root
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=3306

# AI API Keys
GROQ_API_KEY=your_groq_api_key_here

# Optional: Path to Poppler/Tesseract if not in system PATH
# POPPLER_PATH=C:/Program Files/poppler/bin
```
### 5. Setup Database
Make sure your MySQL server is running and you have created a database named recallai_db (or whatever you named it in .env).

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Run the Application
```bash
python manage.py runserver
```
Visit http://127.0.0.1:8000/ in your browser.

## 📖 Usage Guide

**1.Register/Login: Create an account to access your personal dashboard.**

**2.New Chat: Click "+ New Chat" in the sidebar to start a fresh session.**

**3.Upload Files: Click the Paperclip (📎) icon to upload PDFs or Text files.**

**The system will index these files immediately.**

**4.Chat: Type your query. The AI will search your uploaded files and provide an answer based only on that context.**

**5.Manage History: You can delete old chat sessions from the sidebar using the '🗑️' button.**

## 📂 Project Structure
```
RecallAI-ChatBot/
├── ChatBot/                 # Main Django Project Config
│   ├── settings.py          # App settings (DB, Middleware, Installed Apps)
│   ├── urls.py              # Main URL routing
│   └── ...
├── rag_core_app/            # Core Application Logic
│   ├── migrations/          # DB Migrations
│   ├── templates/           # HTML Files (Home, Login, Register)
│   ├── models.py            # DB Models (Document, ChatSession, ChatMessage)
│   ├── rag_utils.py         # RAG Logic (LangChain, FAISS, OCR, Groq)
│   ├── views.py             # API Views & Page Rendering
│   └── ...
├── static/
│   └── css/
│       └── style.css        # Liquid Glassmorphism Styles
├── faiss_indexes/           # Local storage for Vector Embeddings (GitIgnored)
├── media/                   # User uploaded files (GitIgnored)
├── manage.py
└── .env                     # Environment Variables
```

🤝 Contributing
Contributions are welcome! Please fork the repository and create a pull request for any feature updates or bug fixes.

📄 License
This project is open-source and available under the MIT License.
