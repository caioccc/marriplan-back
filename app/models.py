from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class AbstractTimeStamped(models.Model):
    """
    An abstract base class model that provides self-updating 'created' and 'modified' fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserSettings(AbstractTimeStamped):
    language = models.CharField(max_length=10, default='pt')
    theme = models.CharField(max_length=20, default='light')

    def __str__(self):
        return f"Configurações com {self.theme} tema e {self.language} idioma"


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ("noivo", "Noivo(a)"),
        ("convidado", "Convidado"),
        ("admin", "Admin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="noivo")
    is_email_confirmed = models.BooleanField(default=False)
    email_confirmation_token = models.CharField(max_length=128, blank=True, null=True)
    email_confirmation_expiry = models.DateTimeField(blank=True, null=True)
    reset_password_token = models.CharField(max_length=128, blank=True, null=True)
    reset_password_expiry = models.DateTimeField(blank=True, null=True)
    settings = models.OneToOneField(UserSettings, on_delete=models.CASCADE, related_name='user', null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.username


class UserSession(AbstractTimeStamped):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    active_question_id = models.CharField(max_length=100, null=True, blank=True)
    active_question_data = models.JSONField(null=True, blank=True)
    questions_history = models.JSONField(default=list, blank=True)  # Lista de questões apresentadas

    def __str__(self):
        return f"{self.user.username} - {self.session_id}"


class ChatMessage(AbstractTimeStamped):
    session = models.ForeignKey(UserSession, related_name='messages', on_delete=models.CASCADE)
    is_user = models.BooleanField(default=True)
    content = models.TextField()
    thinking_content = models.TextField(blank=True, null=True, help_text='Conteúdo do pensamento/raciocínio da IA')

    def __str__(self):
        return f"{'User' if self.is_user else 'IA'}: {self.content[:30] + '...' if self.content and len(self.content) > 30 else self.content}"


class QuestionReference(AbstractTimeStamped):
    """Referência para questões armazenadas no MongoDB"""
    question_id = models.CharField(max_length=100, unique=True, db_index=True)
    source_file = models.CharField(max_length=200)
    exam = models.CharField(max_length=50, default='')  # ENEM, FUVEST, etc
    subject_area = models.JSONField()  # Lista de áreas
    difficulty = models.CharField(max_length=20)
    year = models.IntegerField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    embedding_id = models.CharField(max_length=100, null=True, blank=True)  # ID no Qdrant

    class Meta:
        db_table = 'question_references'

    def __str__(self):
        return f"Question {self.question_id}"


class UserQuestionHistory(AbstractTimeStamped):
    """Histórico de interações do usuário com questões"""
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE)
    question = models.ForeignKey(QuestionReference, on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=10)  # A, B, C, D, E
    is_correct = models.BooleanField()
    time_spent = models.IntegerField(null=True)  # segundos

    class Meta:
        db_table = 'user_question_history'
        unique_together = ['user_session', 'question']


class Notification(AbstractTimeStamped):
    NOTIFICATION_TYPES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['is_read', '-created_at']

    def __str__(self):
        return f"{self.type.upper()} - {self.title}"


class UserWeddingProfile(AbstractTimeStamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wedding_profile')
    # Dados do noivo(a)
    nome_noivo = models.CharField(max_length=100, blank=True)
    descricao_noivo = models.TextField(blank=True)
    facebook_noivo = models.CharField(max_length=255, blank=True)
    instagram_noivo = models.CharField(max_length=255, blank=True)
    email_noivo = models.EmailField(blank=True)

    nome_noiva = models.CharField(max_length=100, blank=True)
    descricao_noiva = models.TextField(blank=True)
    facebook_noiva = models.CharField(max_length=255, blank=True)
    instagram_noiva = models.CharField(max_length=255, blank=True)
    email_noiva = models.EmailField(blank=True)

    # Dados do evento
    data_casamento = models.DateField(blank=True, null=True)
    hora_casamento = models.TimeField(blank=True, null=True)
    local = models.CharField(max_length=255, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=50, blank=True)
    cep = models.CharField(max_length=20, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    cor_principal = models.CharField(max_length=50, blank=True)
    frase_casal = models.CharField(max_length=255, blank=True)

    # Fotos
    fotos_amigos = models.JSONField(default=list, blank=True)
    fotos_familia = models.JSONField(default=list, blank=True)
    fotos_diversas = models.JSONField(default=list, blank=True)

    # História do casal
    historia = models.TextField(blank=True)

    # Padrinhos: lista de dicts {nome_casal, foto_casal}
    padrinhos = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Perfil de casamento de {self.user.username}"


class WeddingImage(models.Model):
    url = models.URLField()
    id_cloudinary = models.CharField(max_length=255)
    folder = models.CharField(max_length=100, blank=True)
    in_use = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.folder or ''} - {self.id_cloudinary}"


class WeddingSite(AbstractTimeStamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wedding_site')
    status = models.CharField(max_length=20, choices=[('draft', 'Rascunho'), ('published', 'Publicado'), ('inactive', 'Inativo')], default='draft')
    url_slug = models.SlugField(max_length=64, unique=True)
    template = models.CharField(max_length=50, default='classico')
    groom_name = models.CharField(max_length=100, blank=True)
    bride_name = models.CharField(max_length=100, blank=True)
    wedding_date = models.DateField(blank=True, null=True)
    wedding_time = models.TimeField(blank=True, null=True)
    local = models.CharField(max_length=255, blank=True)
    about_us = models.TextField(blank=True)
    rsvp_text = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=20, blank=True)
    district = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    postalcode = models.CharField(max_length=20, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    cover_photo = models.ForeignKey('WeddingImage', null=True, blank=True, on_delete=models.SET_NULL, related_name='cover_for_sites')
    gallery = models.ManyToManyField('WeddingImage', blank=True, related_name='gallery_for_sites')
    palette = models.CharField(max_length=50, blank=True)
    font = models.CharField(max_length=50, blank=True)
    countdown = models.BooleanField(default=True)
    map = models.BooleanField(default=True)
    social = models.BooleanField(default=True)
    last_published_at = models.DateTimeField(blank=True, null=True)
    last_edited_at = models.DateTimeField(auto_now=True)
    visits = models.PositiveIntegerField(default=0)
    rsvp_count = models.PositiveIntegerField(default=0)
    rsvp_conversion = models.FloatField(default=0.0)
    last_visitor = models.CharField(max_length=100, blank=True)
    last_visitor_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Site de {self.user.username} - {self.status}"


class WeddingSiteHistory(AbstractTimeStamped):
    ACTION_CHOICES = [
        ('create', 'Criação'),
        ('edit', 'Edição'),
        ('publish', 'Publicação'),
        ('unpublish', 'Despublicação'),
        ('delete', 'Exclusão'),
    ]
    site = models.ForeignKey(WeddingSite, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ['-created_at']

    def get_action_display(self):
        return dict(self.ACTION_CHOICES).get(self.action, 'Desconhecido')

    def __str__(self):
        return f"{self.site} - {self.get_action_display()} em {self.created_at:%d/%m/%Y %H:%M}"


class ChecklistTask(models.Model):
    PRIORITY_CHOICES = [
        ('high', 'Alta'),
        ('medium', 'Média'),
        ('low', 'Baixa'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('in_progress', 'Em Andamento'),
        ('done', 'Concluído'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checklist_tasks')
    month = models.PositiveSmallIntegerField()  # 1 a 12
    description = models.CharField(max_length=255)
    start_date = models.DateField()
    due_date = models.DateField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    is_template = models.BooleanField(default=False)  # True para tarefas pré-cadastradas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    days_before_event = models.IntegerField(null=True, blank=True, help_text="Dias antes do evento para agrupar no frontend")

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, 'Desconhecido')

    def __str__(self):
        return f"Tarefa de Checklist {self.description} - {self.get_status_display()}"


class ChecklistTaskAttachment(models.Model):
    task = models.ForeignKey(ChecklistTask, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='checklist_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anexo de Tarefa {self.task.description} - {self.file.name}"


class ChecklistTaskShare(models.Model):
    task = models.ForeignKey(ChecklistTask, on_delete=models.CASCADE, related_name='shares')
    email = models.EmailField()
    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tarefa {self.task.description} compartilhada com {self.email}"


class ChecklistTaskNotification(models.Model):
    task = models.ForeignKey(ChecklistTask, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scheduled_for = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notificação de Tarefa {self.task.description} para {self.user.username}"


class Guest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='guests')
    wedding_profile = models.ForeignKey('UserWeddingProfile', on_delete=models.CASCADE, related_name='guests')
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
