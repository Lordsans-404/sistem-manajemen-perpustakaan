import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

class UserManager(BaseUserManager):
    """Manager untuk Custom User."""
    
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("User harus memiliki alamat email")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser harus memiliki is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser harus memiliki is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Model User Custom menggunakan UUID sebagai Primary Key.
    Disesuaikan dengan skema industri dan kesiapan integrasi SSO.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # SSO_ID di-comment untuk kebutuhan boilerplate umum
    # sso_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Timestamp
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        db_table = 'users'  # Sesuai dengan permintaan nama table SQL Anda
        ordering = ['-created_at']

    def __str__(self):
        return self.email
