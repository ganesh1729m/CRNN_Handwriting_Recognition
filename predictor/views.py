import os
import json
import base64
import re
import uuid

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import logout

from .utils import predict_word
from .models import CanvasDrawing


# ----------------------------
# AUTHENTICATION VIEWS
# ----------------------------
def index(request):
    """
    Home page view. Shows whether user is authenticated.
    Handles logout query param to show success message.
    """
    if request.GET.get("logout") == "1":
        messages.success(request, "Successfully logged out.")
    return render(request, "predictor/index.html", {"is_authenticated": request.user.is_authenticated})


def logout_view(request):
    """
    Logs out the user and redirects to home with logout message.
    """
    logout(request)
    return redirect("/?logout=1")


def register(request):
    """
    User registration view.
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})


# ----------------------------
# PREDICTION VIEWS (Open to guests)
# ----------------------------
@csrf_exempt
def upload_canvas(request):
    """
    Accepts a POST request with a base64 canvas image.
    Saves the image, runs prediction, and returns JSON response.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    try:
        body = json.loads(request.body)
        data_url = body.get("image")
        if not data_url:
            return HttpResponseBadRequest("No image received")

        img_match = re.search(r'base64,(.*)', data_url)
        if not img_match:
            return HttpResponseBadRequest("Invalid image format")

        img_bytes = base64.b64decode(img_match.group(1))

        # Save image
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename = f"canvas_{timezone.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}.png"
        path = os.path.join(settings.MEDIA_ROOT, filename)
        with open(path, "wb") as f:
            f.write(img_bytes)

        # Run prediction
        prediction = predict_word(path)

        return JsonResponse({
            "prediction": prediction,
            "file": filename,
            "file_url": f"{settings.MEDIA_URL}{filename}"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ----------------------------
# SAVE CANVAS (requires login)
# ----------------------------
@login_required
@csrf_exempt
def save_canvas(request):
    """
    Saves a canvas drawing for authenticated users.
    Optionally runs prediction and stores it in DB.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    try:
        body = json.loads(request.body)
        image_data = body.get("image")
        if not image_data:
            return HttpResponseBadRequest("Image data required")

        # Decode base64 image
        format_str, img_str = image_data.split(";base64,")
        ext = format_str.split("/")[-1]
        img_bytes = base64.b64decode(img_str)

        # Save file
        save_dir = os.path.join(settings.MEDIA_ROOT, "drawings")
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(img_bytes)

        # Run prediction
        prediction = predict_word(filepath)

        # Save in DB
        drawing = CanvasDrawing.objects.create(
            user=request.user,
            image=f"drawings/{filename}",
            prediction=prediction
        )

        return JsonResponse({
            "success": True,
            "message": "Canvas saved",
            "filename": filename,
            "id": drawing.id,
            "prediction": prediction
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ----------------------------
# GALLERY (requires login)
# ----------------------------
@login_required
def gallery(request):
    """
    Returns a JSON list of all drawings by the authenticated user.
    """
    drawings = CanvasDrawing.objects.filter(user=request.user).order_by("-created_at")
    data = [
        {
            "id": d.id,
            "image": d.image.url,
            "prediction": d.prediction,
            "correct_label": d.correct_label,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for d in drawings
    ]
    return JsonResponse({"items": data})


# ----------------------------
# REPORT CANVAS (requires login)
# ----------------------------
@login_required
@csrf_exempt
def report_canvas(request):
    """
    Accepts POST request to report the correct label for a saved drawing.
    Updates DB and appends to JSONL report log.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    try:
        body = json.loads(request.body)
        filename = body.get("file")
        correct_label = body.get("label")

        if not filename or not correct_label:
            return HttpResponseBadRequest("File and label are required")

        # Fetch drawing
        drawing = get_object_or_404(CanvasDrawing, user=request.user, image__icontains=filename)

        # Update label
        drawing.correct_label = correct_label.upper()
        drawing.save()

        # Append to reports JSONL
        reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        report_file = os.path.join(reports_dir, "reports.jsonl")

        report_entry = {
            "user": request.user.username,
            "file": filename,
            "label": correct_label.upper(),
            "timestamp": timezone.now().isoformat()
        }

        with open(report_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(report_entry) + "\n")

        return JsonResponse({"success": True, "message": "Report saved"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
