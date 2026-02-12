import os
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from .rag_utils import get_answer, process_files_bulk, clear_data, generate_chat_title
from .forms import SignUpForm, UserUpdateForm, UserLoginForm, DocumentForm
from .models import Document, ChatSession, ChatMessage

# === SECURITY CONFIGURATION ===
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.docx', '.pptx', '.xlsx', '.csv', '.png', '.jpg', '.jpeg']

# === AUTHENTICATION ===

def landing(request):
    return render(request, 'landing.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
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
    return redirect('landing')

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
    """
    Optimized upload handler:
    1. Saves all files first.
    2. Collects URLs.
    3. Runs ONE bulk ingestion process for everything.
    """
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        
        # 1. Create/Get Session Logic
        if not session_id or session_id == 'null':
            new_session = ChatSession.objects.create(user=request.user, title="New Uploaded Chat")
            session_id = new_session.id
        
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        
        results = []
        process_queue = [] # Stores both file paths and URLs
        
        # A. Handle File Uploads
        files = request.FILES.getlist('files')
        if files:
            for f in files:
                form = DocumentForm(data={'file': f}, files={'file': f})
                if form.is_valid():
                    doc = form.save(commit=False)
                    doc.name = f.name
                    doc.size = f"{f.size/1024:.2f} KB"
                    doc.save()
                    process_queue.append(doc.file.path)
                    results.append({'name': f.name, 'status': 'Uploaded'})
                else:
                    results.append({'name': f.name, 'status': 'Invalid Type'})

        # B. Handle URL Input (New Feature)
        input_url = request.POST.get('url')
        if input_url:
            print(f"🔗 Processing URL: {input_url}")
            process_queue.append(input_url)
            results.append({'name': input_url, 'status': 'URL Queued'})
        
        # 3. Bulk Process (Files + URLs together)
        if process_queue:
            success = process_files_bulk(process_queue, session.id)
            final_status = 'Indexed' if success else 'Index Failed'
            
            # Update local status for the UI
            for res in results:
                if res['status'] in ['Uploaded', 'URL Queued']: 
                    res['status'] = final_status

            # Add system message
            source_count = len(process_queue)
            ChatMessage.objects.create(session=session, is_user=True, text=f"Uploaded {source_count} sources (Files/URLs).")
            ChatMessage.objects.create(session=session, is_user=False, text="I have analyzed these sources. Ask me anything!")

            return JsonResponse({'status': 'success', 'files': results, 'session_id': session.id})
        
        return JsonResponse({'status': 'error', 'message': 'No files or URL provided'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@never_cache
def chat_api(request):
    """
    Streaming Chat API:
    Returns a StreamingHttpResponse to enable 'line-by-line' generation.
    """
    if request.method == "POST":
        user_msg = request.POST.get('message', '').strip()
        session_id = request.POST.get('session_id')
        
        if not user_msg:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Create Session if needed
        if not session_id or session_id == 'null':
            session = ChatSession.objects.create(user=request.user, title=user_msg[:30])
            session_id = session.id
            is_new_session = True
        else:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
            is_new_session = False
            
        # Save User Message
        ChatMessage.objects.create(session=session, is_user=True, text=user_msg)
        
        # Generator for Streaming
        def event_stream():
            full_response = ""
            try:
                # Stream chunks from RAG/LLM
                for chunk in get_answer(user_msg, session.id):
                    full_response += chunk
                    yield chunk
                
                # After stream finishes, save the full response
                ChatMessage.objects.create(session=session, is_user=False, text=full_response)
                
                # Update title if new session
                if is_new_session:
                    new_title = generate_chat_title(user_msg, full_response)
                    session.title = new_title
                    session.save()
                    
            except Exception as e:
                err = f"Error: {str(e)}"
                ChatMessage.objects.create(session=session, is_user=False, text=err)
                yield err

        # Return Streaming Response
        response = StreamingHttpResponse(event_stream(), content_type='text/plain')
        
        # Send Metadata in Headers (Client can read these)
        response['X-Session-ID'] = str(session.id)
        if is_new_session:
            response['X-Session-Title'] = session.title
            
        return response

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