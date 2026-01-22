from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .rag_utils import get_answer, process_file
from .forms import DocumentForm 
from .models import Document, ChatSession, ChatMessage

# === AUTHENTICATION VIEWS (Restored) ===

def landing(request):
    return render(request, 'landing.html')

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

# === NEW APP VIEWS (Home, Chat, Upload) ===

@login_required
def home(request):
    # Get or Create a session based on URL parameter
    session_id = request.GET.get('session_id')
    current_session = None
    
    if session_id:
        try:
            current_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            current_session = None

    # Get all past sessions for the Sidebar
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
    
    # Empty form for compatibility
    form = DocumentForm() 
    
    return render(request, 'home.html', {
        'sessions': sessions, 
        'current_session': current_session,
        'form': form
    })

def upload_api(request):
    # Handles the Multi-File Upload from the new UI
    if request.method == 'POST' and request.FILES.getlist('files'):
        files = request.FILES.getlist('files')
        results = []
        
        for f in files:
            # Save to DB
            doc = Document.objects.create(file=f, name=f.name, size=f"{f.size/1024:.2f} KB")
            # Index the file immediately
            process_file(doc.file.path)
            results.append({'name': f.name, 'status': 'Indexed'})
            
        return JsonResponse({'status': 'success', 'files': results})
    return JsonResponse({'status': 'error'}, status=400)

def chat_api(request):
    if request.method == "POST":
        user_msg = request.POST.get('message')
        session_id = request.POST.get('session_id')
        
        if not user_msg:
             return JsonResponse({'error': 'Empty message'}, status=400)

        # 1. Manage Session (Create New or Get Existing)
        if not session_id or session_id == 'null':
            session = ChatSession.objects.create(user=request.user, title=user_msg[:30])
        else:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create(user=request.user, title=user_msg[:30])
            
        # 2. Save User Message
        ChatMessage.objects.create(session=session, is_user=True, text=user_msg)
        
        # 3. Get AI Response
        bot_response = get_answer(user_msg)
        
        # 4. Save Bot Message
        ChatMessage.objects.create(session=session, is_user=False, text=bot_response)
        
        return JsonResponse({
            'response': bot_response, 
            'session_id': session.id,
            'session_title': session.title
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)