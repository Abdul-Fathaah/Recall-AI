from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .rag_utils import get_answer, process_file, clear_data, generate_chat_title
from .forms import DocumentForm, SignUpForm, UserUpdateForm
from .models import Document, ChatSession, ChatMessage

# === AUTHENTICATION ===
def landing(request): return render(request, 'landing.html')
def register(request):
    if request.method == "POST":
        form = SignUpForm(request.POST) # Use the new form
        if form.is_valid():
            login(request, form.save())
            return redirect('home')
    else:
        form = SignUpForm()

    # Inject Glass Styles
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'glass-input', 'placeholder': field.label})

    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    else:
        form = AuthenticationForm()

    for field in form.fields.values():
        field.widget.attrs.update({
            'class': 'glass-input',
            'placeholder': field.label
        })

    return render(request, 'login.html', {'form': form})
def user_logout(request): logout(request); return redirect('login')

# === APP VIEWS ===

@login_required
def home(request):
    session_id = request.GET.get('session_id')
    current_session = None
    if session_id:
        try:
            current_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            current_session = None
            
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'home.html', {'sessions': sessions, 'current_session': current_session})

def upload_api(request):
    # Handles File Upload
    if request.method == 'POST' and request.FILES.getlist('files'):
        session_id = request.POST.get('session_id')
        
        # 1. CREATE SESSION IF NULL (Critical for "New Chat" uploads)
        if not session_id or session_id == 'null':
            new_session = ChatSession.objects.create(user=request.user, title="New Uploaded Chat")
            session_id = new_session.id
        
        files = request.FILES.getlist('files')
        results = []
        
        for f in files:
            doc = Document.objects.create(file=f, name=f.name, size=f"{f.size/1024:.2f} KB")
            # 2. PASS SESSION ID TO PROCESSOR
            process_file(doc.file.path, session_id)
            results.append({'name': f.name, 'status': 'Indexed'})
            
        # 3. Save a system message in the chat
        try:
            session = ChatSession.objects.get(id=session_id)
            file_names = ", ".join([f.name for f in files])
            ChatMessage.objects.create(session=session, is_user=True, text=f"Uploaded files: {file_names}")
            ChatMessage.objects.create(session=session, is_user=False, text="I have read these files. Ask me anything about them!")
        except:
            pass

        return JsonResponse({'status': 'success', 'files': results, 'session_id': session_id})
    return JsonResponse({'status': 'error'}, status=400)

def chat_api(request):
    if request.method == "POST":
        user_msg = request.POST.get('message')
        session_id = request.POST.get('session_id')
        if not user_msg: return JsonResponse({'error': 'Empty'}, status=400)

        is_new = False
        if not session_id or session_id == 'null':
            session = ChatSession.objects.create(user=request.user, title=user_msg[:30])
            is_new = True
        else:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            
        ChatMessage.objects.create(session=session, is_user=True, text=user_msg)
        
        # Pass Session ID to AI
        bot_response = get_answer(user_msg, session.id)
        
        ChatMessage.objects.create(session=session, is_user=False, text=bot_response)
        
        if is_new:
            session.title = generate_chat_title(user_msg, bot_response)
            session.save()
        
        return JsonResponse({'response': bot_response, 'session_id': session.id, 'session_title': session.title})
    return JsonResponse({'error': 'Invalid'}, status=400)

def delete_chat_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    clear_data(session.id) # Wipe only this chat's brain
    session.delete()
    return redirect('home')

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('home')
    return redirect('home')