from django.contrib import admin
from django.urls import path
from rag_core_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Pages
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('home/', views.home, name='home'),
    
    # API Endpoints (The brain)
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/upload/', views.upload_api, name='upload_api'), # <--- This was likely missing!
]