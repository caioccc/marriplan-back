from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from app.models import ChecklistTask
from django.contrib.auth import get_user_model
from datetime import date, timedelta

PRESET_TASKS = [
    # 12 meses antes
    {'month': 12, 'description': 'Definir a data do casamento', 'priority': 'high', 'start_offset': 0, 'due_offset': 10},
    {'month': 12, 'description': 'Reservar a igreja/cerimônia', 'priority': 'high', 'start_offset': 0, 'due_offset': 15},
    {'month': 12, 'description': 'Reservar o local da festa', 'priority': 'high', 'start_offset': 0, 'due_offset': 20},
    {'month': 12, 'description': 'Contratar cerimonial', 'priority': 'high', 'start_offset': 0, 'due_offset': 25},
    {'month': 12, 'description': 'Criar lista de convidados', 'priority': 'medium', 'start_offset': 0, 'due_offset': 30},
    {'month': 12, 'description': 'Escolher o estilo e tema do casamento', 'priority': 'medium', 'start_offset': 0, 'due_offset': 30},
    {'month': 12, 'description': 'Contratar Papelaria', 'priority': 'medium', 'start_offset': 0, 'due_offset': 30},
    # 11 meses antes
    {'month': 11, 'description': 'Contratar fotógrafo', 'priority': 'high', 'start_offset': 30, 'due_offset': 40},
    {'month': 11, 'description': 'Contratar filmagem', 'priority': 'medium', 'start_offset': 30, 'due_offset': 45},
    {'month': 11, 'description': 'Escolher buffet', 'priority': 'high', 'start_offset': 30, 'due_offset': 50},
    {'month': 11, 'description': 'Escolher o vestido de noiva', 'priority': 'high', 'start_offset': 30, 'due_offset': 60},
    {'month': 11, 'description': 'Definir o tema da decoração', 'priority': 'medium', 'start_offset': 30, 'due_offset': 60},
    # 10 meses antes
    {'month': 10, 'description': 'Comprar sapato da noiva', 'priority': 'medium', 'start_offset': 60, 'due_offset': 70},
    {'month': 10, 'description': 'Definir cabelo e maquiagem', 'priority': 'medium', 'start_offset': 60, 'due_offset': 75},
    {'month': 10, 'description': 'Escolher joias', 'priority': 'low', 'start_offset': 60, 'due_offset': 80},
    {'month': 10, 'description': 'Agendar o dia da noiva', 'priority': 'medium', 'start_offset': 60, 'due_offset': 85},
    # 9 meses antes
    {'month': 9, 'description': 'Escolher cores da decoração', 'priority': 'medium', 'start_offset': 90, 'due_offset': 100},
    {'month': 9, 'description': 'Contratar decoração', 'priority': 'high', 'start_offset': 90, 'due_offset': 110},
    {'month': 9, 'description': 'Definir damas de honra e pajens', 'priority': 'medium', 'start_offset': 90, 'due_offset': 110},
    {'month': 9, 'description': 'Escolher e convidar padrinhos e madrinhas', 'priority': 'medium', 'start_offset': 90, 'due_offset': 120},
    {'month': 9, 'description': 'Contratar DJ ou banda', 'priority': 'high', 'start_offset': 90, 'due_offset': 120},
    # 8 meses antes
    {'month': 8, 'description': 'Escolher e comprar lembrancinhas', 'priority': 'medium', 'start_offset': 120, 'due_offset': 130},
    {'month': 8, 'description': 'Escolher bouquet', 'priority': 'medium', 'start_offset': 120, 'due_offset': 135},
    {'month': 8, 'description': 'Escolher alianças', 'priority': 'high', 'start_offset': 120, 'due_offset': 140},
    {'month': 8, 'description': 'Escolher modelo do bolo', 'priority': 'medium', 'start_offset': 120, 'due_offset': 145},
    {'month': 8, 'description': 'Criar e enviar o “Save the Date”', 'priority': 'medium', 'start_offset': 120, 'due_offset': 150},
    # 7 meses antes
    {'month': 7, 'description': 'Definir estilo da cerimônia', 'priority': 'medium', 'start_offset': 150, 'due_offset': 160},
    {'month': 7, 'description': 'Escolher música da cerimônia', 'priority': 'medium', 'start_offset': 150, 'due_offset': 165},
    {'month': 7, 'description': 'Escolher traje do noivo', 'priority': 'high', 'start_offset': 150, 'due_offset': 170},
    {'month': 7, 'description': 'Verificar iluminação e som', 'priority': 'medium', 'start_offset': 150, 'due_offset': 175},
    # 6 meses antes
    {'month': 6, 'description': 'Agendar lua de mel e comprar passagens', 'priority': 'high', 'start_offset': 180, 'due_offset': 190},
    {'month': 6, 'description': 'Criar o site do casamento', 'priority': 'medium', 'start_offset': 180, 'due_offset': 195},
    {'month': 6, 'description': 'Encomendar bolo e doces', 'priority': 'medium', 'start_offset': 180, 'due_offset': 200},
    {'month': 6, 'description': 'Escolher os convites e iniciar produção', 'priority': 'medium', 'start_offset': 180, 'due_offset': 205},
    # 5 meses antes
    {'month': 5, 'description': 'Comprar bouquet das damas', 'priority': 'low', 'start_offset': 210, 'due_offset': 215},
    {'month': 5, 'description': 'Comprar bouquet para jogar', 'priority': 'low', 'start_offset': 210, 'due_offset': 220},
    {'month': 5, 'description': 'Comprar terço, colar e brincos', 'priority': 'low', 'start_offset': 210, 'due_offset': 225},
    {'month': 5, 'description': 'Comprar topo de bolo', 'priority': 'low', 'start_offset': 210, 'due_offset': 230},
    {'month': 5, 'description': 'Criar scrapbook com fotos', 'priority': 'low', 'start_offset': 210, 'due_offset': 235},
    {'month': 5, 'description': 'Comprar gravatinhas para lembranças', 'priority': 'low', 'start_offset': 210, 'due_offset': 240},
    {'month': 5, 'description': 'Reservar carro para os noivos', 'priority': 'medium', 'start_offset': 210, 'due_offset': 245},
    # 4 meses antes
    {'month': 4, 'description': 'Encomendar traje completo do noivo', 'priority': 'medium', 'start_offset': 240, 'due_offset': 250},
    {'month': 4, 'description': 'Provar o vestido da noiva', 'priority': 'high', 'start_offset': 240, 'due_offset': 255},
    {'month': 4, 'description': 'Definir detalhes da lua de mel', 'priority': 'medium', 'start_offset': 240, 'due_offset': 260},
    {'month': 4, 'description': 'Iniciar compra de lingerie para lua de mel', 'priority': 'low', 'start_offset': 240, 'due_offset': 265},
    # 3 meses antes
    {'month': 3, 'description': 'Provar o vestido e ajustar', 'priority': 'high', 'start_offset': 270, 'due_offset': 275},
    {'month': 3, 'description': 'Definir certidão e votos de casamento', 'priority': 'medium', 'start_offset': 270, 'due_offset': 280},
    {'month': 3, 'description': 'Criar a tabela de assentos', 'priority': 'medium', 'start_offset': 270, 'due_offset': 285},
    {'month': 3, 'description': 'Agendar prova de cabelo e maquiagem', 'priority': 'medium', 'start_offset': 270, 'due_offset': 290},
    {'month': 3, 'description': 'Definir transporte dos noivos', 'priority': 'medium', 'start_offset': 270, 'due_offset': 295},
    {'month': 3, 'description': 'Escolher músicas da cerimônia', 'priority': 'medium', 'start_offset': 270, 'due_offset': 300},
    # 2 meses antes
    {'month': 2, 'description': 'Entregar os convites', 'priority': 'medium', 'start_offset': 300, 'due_offset': 305},
    {'month': 2, 'description': 'Realizar chá de panela/bar', 'priority': 'medium', 'start_offset': 300, 'due_offset': 310},
    {'month': 2, 'description': 'Comprar itens para lua de mel', 'priority': 'low', 'start_offset': 300, 'due_offset': 315},
    # 1 mês antes
    {'month': 1, 'description': 'Reunião final com cerimonial/DJ/banda', 'priority': 'high', 'start_offset': 330, 'due_offset': 335},
    {'month': 1, 'description': 'Teste de penteado e maquiagem', 'priority': 'medium', 'start_offset': 330, 'due_offset': 340},
    {'month': 1, 'description': 'Prova final do vestido', 'priority': 'high', 'start_offset': 330, 'due_offset': 345},
    {'month': 1, 'description': 'Realizar peeling, limpeza de pele e outros cuidados estéticos', 'priority': 'low', 'start_offset': 330, 'due_offset': 350},
    {'month': 1, 'description': 'Finalizar lista de confirmação de presença', 'priority': 'medium', 'start_offset': 330, 'due_offset': 355},
    # 15 dias antes
    {'month': 0, 'description': 'Confirmar com todos os fornecedores', 'priority': 'high', 'start_offset': 350, 'due_offset': 351},
    {'month': 0, 'description': 'Comprar brindes para pista de dança', 'priority': 'low', 'start_offset': 350, 'due_offset': 352},
    {'month': 0, 'description': 'Conferir roupas do noivo e da noiva', 'priority': 'medium', 'start_offset': 350, 'due_offset': 353},
    # 10 dias antes
    {'month': 0, 'description': 'Fazer prévia do penteado e maquiagem', 'priority': 'medium', 'start_offset': 355, 'due_offset': 356},
    # 1 semana antes
    {'month': 0, 'description': 'Ensaiar a cerimônia', 'priority': 'medium', 'start_offset': 358, 'due_offset': 359},
    {'month': 0, 'description': 'Organizar a decoração final', 'priority': 'medium', 'start_offset': 358, 'due_offset': 360},
    {'month': 0, 'description': 'Conferir e preparar a roupa do noivo', 'priority': 'medium', 'start_offset': 358, 'due_offset': 360},
    # 5 dias antes
    {'month': 0, 'description': 'Fazer massagem relaxante', 'priority': 'low', 'start_offset': 362, 'due_offset': 363},
    {'month': 0, 'description': 'Depilação e cuidados estéticos', 'priority': 'low', 'start_offset': 362, 'due_offset': 364},
    {'month': 0, 'description': 'Retirar vestido e traje do noivo', 'priority': 'medium', 'start_offset': 362, 'due_offset': 365},
    # 2 dias antes
    {'month': 0, 'description': 'Fazer unha e pedicure', 'priority': 'low', 'start_offset': 365, 'due_offset': 366},
    {'month': 0, 'description': 'Últimos retoques na estética', 'priority': 'low', 'start_offset': 365, 'due_offset': 366},
    # 1 dia antes
    {'month': 0, 'description': 'Levar itens para o local da festa', 'priority': 'medium', 'start_offset': 366, 'due_offset': 367},
    {'month': 0, 'description': 'Arrumar as malas da lua de mel', 'priority': 'medium', 'start_offset': 366, 'due_offset': 367},
    {'month': 0, 'description': 'Tentar descansar e dormir bem', 'priority': 'low', 'start_offset': 366, 'due_offset': 367},
    # Após o casamento
    {'month': 0, 'description': 'Enviar cartões de agradecimento', 'priority': 'medium', 'start_offset': 370, 'due_offset': 380},
    {'month': 0, 'description': 'Compartilhar fotos com os convidados', 'priority': 'medium', 'start_offset': 370, 'due_offset': 380},
]

User = get_user_model()

@receiver(post_save, sender=User)
def create_checklist_for_new_user(sender, instance, created, **kwargs):
    if created and getattr(instance, 'is_active', False):
      for task in PRESET_TASKS:
        exists = ChecklistTask.objects.filter(
          user=instance,
          month=task['month'],
          description=task['description']
        ).exists()
        if not exists:
          days_before_event = None
          # Definição dos dias para agrupamento frontend usando offset
          if task['month'] == 0:
            if task['start_offset'] == 350:
              days_before_event = 15
            elif task['start_offset'] == 355:
              days_before_event = 10
            elif task['start_offset'] == 358:
              days_before_event = 7
            elif task['start_offset'] == 362:
              days_before_event = 5
            elif task['start_offset'] == 365:
              days_before_event = 2
            elif task['start_offset'] == 366:
              days_before_event = 1
            elif task['start_offset'] == 370:
              days_before_event = -1
          ChecklistTask.objects.create(
            user=instance,
            month=task['month'],
            description=task['description'],
            priority=task['priority'],
            start_date=date.today() + timedelta(days=task['start_offset']),
            due_date=date.today() + timedelta(days=task['due_offset']),
            is_template=True,
            days_before_event=days_before_event,
          )
