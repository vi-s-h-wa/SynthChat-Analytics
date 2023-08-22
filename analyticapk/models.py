from django.db import models

# Create your models here.
class Messages(models.Model):
    username = models.CharField(max_length=255, default=None)
    user = models.CharField(max_length=255, default=None)
    reply = models.CharField(max_length=255)
    emotion = models.CharField(max_length=255)

class Userdetails(models.Model):
    username = models.CharField(max_length=255, default=None)
    password = models.CharField(max_length=255)
    email = models.CharField(max_length=255)

class UserSession(models.Model):
    username = models.CharField(max_length=255, default=None)
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(null=True, blank=True)