from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Posicao(models.TextChoices):
    GOLEIRO = 'GOL', 'Goleiro'
    ZAGUEIRO = 'ZAG', 'Zagueiro'
    MEIA = 'MEI', 'Meia'
    ATACANTE = 'ATA', 'Atacante'


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Jogador do Racha. Faz login com e-mail e senha."""

    email = models.EmailField('e-mail', unique=True)
    nome = models.CharField(max_length=80)
    posicao = models.CharField(max_length=3, choices=Posicao.choices, default=Posicao.MEIA)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self):
        return f'{self.nome} <{self.email}>'
