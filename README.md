# Recall AI - Personalized RAG Chatbot

## ⚠️ Security Setup (Read Before Cloning)

This project uses environment variables for all secrets. **Never commit your `.env` file.**

1. Copy the template: `cp .env.example .env`
2. Fill in your actual values in `.env`
3. Generate a Django secret key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
4. Get a free Groq API key at: https://console.groq.com

The `.env` file is already in `.gitignore`. If you have already committed secrets by mistake, rotate them immediately (new Groq key, new Django secret key, new DB password).

**Recall AI** is a powerful, Django-based AI assistant that uses **Retrieval-Augmented Generation (RAG)** to allow users to upload documents (PDFs, text files, etc.) and chat with them intelligently. It features a modern **Liquid Glassmorphism UI**, persistent chat history, and session-based memory using **FAISS** and **Groq's Llama 3**.

## 🚀 Features

* **📄 Document Q&A**: Upload multiple PDF, TXT, DOCX, PPTX, XLSX, or CSV files and ask questions based on their content.
* **🧠 Advanced RAG Engine**: Uses **LangChain** and **FAISS** vector stores to retrieve relevant context for every query.
* **⚡ Fast Inference**: Powered by **Groq API** (Llama-3.1-8b-instant) for lightning-fast responses.
* **👁️ OCR Capabilities**: Integrated **Tesseract OCR** & **pdf2image** to extract text from scanned documents or images.
* **💾 Persistent Sessions**: Chat history is saved in a MySQL database. Create multiple "Chat Sessions," each with its own isolated document context.
* **🎨 Modern UI**: A sleek, fully responsive **Liquid Glassmorphism** interface designed with deep gradients and frosted glass effects.
* **🔐 User Authentication**: Secure Login/Register system to keep user data private.

## 🛠️ Tech Stack

* **Backend:** Django 4.x, Python 3.10+
* **AI/ML:** LangChain, FAISS (Vector Store), Groq API (LLM), Sentence Transformers
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
git clone https://github.com/yourusername/recall-ai.git
cd recall-ai
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

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add the following:

```env
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
# TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### 5. Setup Database
Make sure your MySQL server is running and you have created a database named `recallai_db` (or whatever you named it in `.env`).

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

1.  **Register/Login**: Create an account to access your personal dashboard.
2.  **New Chat**: Click "+ New Chat" in the sidebar to start a fresh session.
3.  **Upload Files**: Click the Paperclip (📎) icon to upload PDFs or Text files. The system will index these files immediately.
4.  **Chat**: Type your query. The AI will search your uploaded files and provide an answer based only on that context.
5.  **Manage History**: View past conversations or clear sessions using the sidebar controls.

## 📂 Project Structure
```
Recall-AI/
├── ChatBot/                 # Main Django Project Config
│   ├── settings.py          # App settings
│   ├── urls.py              # Main URL routing
│   └── ...
├── rag_core_app/            # Core Application Logic
│   ├── migrations/          # DB Migrations
│   ├── templates/           # HTML Files (Home, Login, Register)
│   │   ├── landing.html
│   │   ├── register.html
│   │   ├── login.html
│   │   └── home.html
│   ├── models.py            # DB Models (Document, ChatSession, ChatMessage)
│   ├── rag_utils.py         # RAG Logic (LangChain, FAISS, OCR, Groq)
│   ├── views.py             # API Views & Page Rendering
│   └── forms.py             # Forms for Auth and Uploads
├── static/
│   ├── css/
│   │   ├── auth.css         # Auth specific styles
│   │   ├── dashboard.css    # Main app styles
│   │   ├── landing.css      # Landing page styles
│   │   └── style.css        # Shared/Base styles
│   └── js/
│       ├── dashboard.js     # Chat interactivity and file upload
│       └── theme.js         # Theme handling
├── faiss_indexes/           # Local storage for Vector Embeddings (GitIgnored)
├── media/                   # User uploaded files (GitIgnored)
├── manage.py
├── requirements.txt         # Project Dependencies
└── .env                     # Environment Variables
```

## 🤝 Contributing
Contributions are welcome! Please fork the repository and create a pull request for any feature updates or bug fixes.

## 📄 License
This project is open-source and available under the MIT License.
