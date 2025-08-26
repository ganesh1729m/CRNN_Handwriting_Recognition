from django.db import models
from django.contrib.auth.models import User

class CanvasDrawing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="drawings")
    image = models.ImageField(upload_to="canvases/")
    prediction = models.CharField(max_length=100, blank=True, null=True)
    correct_label = models.CharField(max_length=100, blank=True, null=True)  # for report button later
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.prediction or 'Unlabeled'}"


class ReportedCanvas(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="reports/")
    label = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
