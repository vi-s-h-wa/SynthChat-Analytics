from django.contrib import admin
from django.urls import path
from analyticapk import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.login.as_view(),name='login'),
    path('chatgpt/', views.chatgpt,name='chatgpt'),
    path('search/', views.search,name='search'),
    path('register/', views.register.as_view(),name='register'),
    path('logout/', views.Logout.as_view(), name='logout'),
]
