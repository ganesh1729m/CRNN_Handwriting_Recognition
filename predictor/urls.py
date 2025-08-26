from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", views.index, name="index"),
    path("upload_canvas/", views.upload_canvas, name="upload_canvas"),
    path("save_canvas/", views.save_canvas, name="save_canvas"),
    path("gallery/", views.gallery, name="gallery"),
    path("report_canvas/", views.report_canvas, name="report_canvas"),
    
    # 🔑 Auth routes
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),  
]
