import os
import json
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.core.cache import cache
from .rag_utils import get_answer, process_files_bulk, clear_data, generate_chat_title
from .forms import SignUpForm, UserUpdateForm, UserLoginForm, DocumentForm
from .models import Document, ChatSession, ChatMessage

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


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


@require_POST
def user_logout(request):
    logout(request)
    return redirect('landing')


def rate_limit_user(max_calls=15, period=60):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                key = f"rate_limit_chat_{request.user.id}"
                calls = cache.get(key, 0)
                if calls >= max_calls:
                    return JsonResponse(
                        {'error': f'Rate limit exceeded. Max {max_calls} messages per minute.'},
                        status=429
                    )
                cache.set(key, calls + 1, period)
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


@login_required
@never_cache
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


@login_required
def upload_api(request):
    if request.method == 'POST':
        session_id = request.POST.get('session_id')

        if not session_id or session_id == 'null':
            new_session = ChatSession.objects.create(user=request.user, title="New Uploaded Chat")
            session_id = new_session.id

        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        results = []
        process_queue = []

        for f in request.FILES.getlist('files'):
            if f.size > MAX_UPLOAD_SIZE:
                results.append({'name': f.name, 'status': f'Rejected: exceeds 10MB ({f.size / 1024 / 1024:.1f}MB)'})
                continue

            form = DocumentForm(data={}, files={'file': f})
            if form.is_valid():
                doc = form.save(commit=False)
                doc.name = f.name
                doc.size = f"{f.size/1024:.2f} KB"
                doc.session = session
                doc.save()
                process_queue.append(doc.file.path)
                results.append({'name': f.name, 'status': 'Uploaded'})
            else:
                results.append({'name': f.name, 'status': 'Invalid Type'})

        input_url = request.POST.get('url')
        if input_url:
            process_queue.append(input_url)
            results.append({'name': input_url, 'status': 'URL Queued'})

        if process_queue:
            success = process_files_bulk(process_queue, session.id)
            final_status = 'Indexed' if success else 'Index Failed'
            for res in results:
                if res['status'] in ['Uploaded', 'URL Queued']:
                    res['status'] = final_status

            ChatMessage.objects.create(
                session=session, is_user=True,
                text=f"Uploaded {len(process_queue)} source(s)."
            )
            ChatMessage.objects.create(
                session=session, is_user=False,
                text="I have analyzed these sources. Ask me anything!"
            )
            return JsonResponse({'status': 'success', 'files': results, 'session_id': session.id})

        if results:
            return JsonResponse({
                'status': 'error',
                'message': 'All uploads were rejected. Check file types and sizes.',
                'files': results
            }, status=400)

        return JsonResponse({'status': 'error', 'message': 'No files or URL provided'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
@never_cache
@rate_limit_user(max_calls=15, period=60)
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    user_msg = request.POST.get('message', '').strip()
    session_id = request.POST.get('session_id')

    if not user_msg:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    if not session_id or session_id == 'null':
        session = ChatSession.objects.create(user=request.user, title=user_msg[:30])
        session_id = session.id
        is_new_session = True
    else:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        is_new_session = False

    ChatMessage.objects.create(session=session, is_user=True, text=user_msg)

    def event_stream():
        full_response = ""
        try:
            for chunk in get_answer(user_msg, session.id):
                full_response += chunk
                yield chunk

            ChatMessage.objects.create(session=session, is_user=False, text=full_response)

            if is_new_session:
                new_title = generate_chat_title(user_msg, full_response[:300])
                session.title = new_title
                session.save()
                yield f"\n__META__:{json.dumps({'session_id': str(session.id), 'title': new_title})}"

        except Exception as e:
            err = f"Error: {str(e)}"
            ChatMessage.objects.create(session=session, is_user=False, text=err)
            yield err

    response = StreamingHttpResponse(event_stream(), content_type='text/plain')
    response['X-Session-ID'] = str(session.id)
    if is_new_session:
        response['X-Session-Title'] = session.title
    return response


@login_required
def delete_chat_session(request, session_id):
    if request.method == "POST":
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        for doc in session.documents.all():
            if doc.file and os.path.exists(doc.file.path):
                try:
                    os.remove(doc.file.path)
                except OSError:
                    pass
        clear_data(session.id)
        session.delete()
    return redirect('home')


@login_required
def rename_chat_session(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        new_title = request.POST.get('new_title', '').strip()
        if new_title:
            session.title = new_title[:50]
            session.save()
    return redirect('home')


@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
    return redirect('home')