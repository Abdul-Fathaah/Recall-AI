import os
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import ValidationError
from .rag_utils import get_answer, process_file, clear_data, generate_chat_title
from .forms import SignUpForm, UserUpdateForm, UserLoginForm
from .models import Document, ChatSession, ChatMessage

# === SECURITY CONFIGURATION ===
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.docx', '.pptx', '.xlsx', '.csv']

# === AUTHENTICATION ===

def landing(request):
    return render(request, 'landing.html')

def register(request):
    #if request.user.is_authenticated:
    #    return redirect('home')
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    #if request.user.is_authenticated:
    #    return redirect('home')
    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    else:
        form = UserLoginForm()
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

# === SECURE APP VIEWS ===

@login_required
@never_cache
def home(request):
    session_id = request.GET.get('session_id')
    current_session = None
    
    # Validation: Ensure user owns the session
    if session_id:
        try:
            current_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            current_session = None
            
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'home.html', {'sessions': sessions, 'current_session': current_session})

@login_required
def upload_api(request):
    if request.method == 'POST' and request.FILES.getlist('files'):
        session_id = request.POST.get('session_id')
        
        # 1. Create session if needed
        if not session_id or session_id == 'null':
            new_session = ChatSession.objects.create(user=request.user, title="New Uploaded Chat")
            session_id = new_session.id
        
        # 2. Validate Session Ownership
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        
        files = request.FILES.getlist('files')
        results = []
        
        for f in files:
            # === SECURITY CHECK: File Extension ===
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                return JsonResponse({'status': 'error', 'message': f'File type {ext} not allowed'}, status=400)
            
            # === SECURITY CHECK: File Size ===
            if f.size > MAX_UPLOAD_SIZE:
                return JsonResponse({'status': 'error', 'message': f'{f.name} is too large (Max 10MB)'}, status=400)
            
            # Process Valid File
            doc = Document.objects.create(file=f, name=f.name, size=f"{f.size/1024:.2f} KB")
            process_file(doc.file.path, session.id)
            results.append({'name': f.name, 'status': 'Indexed'})
            
        # Add system messages
        file_names = ", ".join([f.name for f in files])
        ChatMessage.objects.create(session=session, is_user=True, text=f"Uploaded files: {file_names}")
        ChatMessage.objects.create(session=session, is_user=False, text="I have analyzed these documents. Ask me anything!")

        return JsonResponse({'status': 'success', 'files': results, 'session_id': session.id})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@never_cache
def chat_api(request):
    if request.method == "POST":
        user_msg = request.POST.get('message', '').strip()
        session_id = request.POST.get('session_id')
        
        # Validation: Empty Message
        if not user_msg:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Validation: Message Length (Prevent DoS with massive text)
        if len(user_msg) > 5000:
            return JsonResponse({'error': 'Message too long (Max 5000 chars)'}, status=400)

        is_new = False
        if not session_id or session_id == 'null':
            session = ChatSession.objects.create(user=request.user, title=user_msg[:30])
            is_new = True
        else:
            # Validation: Ensure user owns the session
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                 return JsonResponse({'error': 'Unauthorized access to session'}, status=403)
            
        ChatMessage.objects.create(session=session, is_user=True, text=user_msg)
        
        # Get AI Response
        try:
            bot_response = get_answer(user_msg, session.id)
        except Exception as e:
            bot_response = "I encountered an error processing your request."
        
        ChatMessage.objects.create(session=session, is_user=False, text=bot_response)
        
        if is_new:
            session.title = generate_chat_title(user_msg, bot_response)
            session.save()
        
        return JsonResponse({
            'response': bot_response, 
            'session_id': session.id, 
            'session_title': session.title
        })
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def delete_chat_session(request, session_id):
    if request.method == "POST":
        # Secure delete: ensure session belongs to request.user
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        clear_data(session.id)
        session.delete()
        return redirect('home')
    return redirect('home')

@login_required
def rename_chat_session(request, session_id):
    if request.method == 'POST':
        # Secure rename: ensure session belongs to request.user
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        new_title = request.POST.get('new_title', '').strip()
        if new_title:
            session.title = new_title[:50]  # Enforce length limit
            session.save()
    return redirect('home')

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
    return redirect('home')