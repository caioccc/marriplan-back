# app/constants.py

EMAIL_CONFIRMATION_HTML_TEMPLATE = """
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
      <h2 style="color: #2d8cff;">Bem-vindo ao Marriplan!</h2>
      <p>Olá <b>{email}</b>,</p>
      <p>Obrigado por se registrar! Para ativar sua conta, confirme seu e-mail clicando no botão abaixo:</p>
      <p style="text-align: center;">
        <a href="{confirmation_link}" style="background: #2d8cff; color: #fff; padding: 12px 24px; border-radius: 4px; text-decoration: none; font-weight: bold;">
          Confirmar e-mail
        </a>
      </p>
      <p>Ou copie e cole este link no navegador:<br>
        <a href="{confirmation_link}">{confirmation_link}</a>
      </p>
      <hr>
      <small>Se você não criou esta conta, ignore este e-mail.</small>
    </div>
  </body>
</html>
"""

RESET_PASSWORD_EMAIL_TEMPLATE = """
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
      <h2 style="color: #2d8cff;">Redefinição de senha - Marriplan</h2>
      <p>Olá <b>{email}</b>,</p>
      <p>Recebemos uma solicitação para redefinir sua senha. Para continuar, clique no botão abaixo:</p>
      <p style="text-align: center;">
        <a href="{reset_link}" style="background: #2d8cff; color: #fff; padding: 12px 24px; border-radius: 4px; text-decoration: none; font-weight: bold;">
          Redefinir senha
        </a>
      </p>
      <p>Ou copie e cole este link no navegador:<br>
        <a href="{reset_link}">{reset_link}</a>
      </p>
      <hr>
      <small>Se você não solicitou esta alteração, ignore este e-mail.</small>
    </div>
  </body>
</html>
"""

EMAIL_WEDDING_SITE_CREATE_SUBJECT = '🎉 Seu site de casamento foi criado!'
EMAIL_WEDDING_SITE_CREATE_BODY = """
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
      <h2 style="color: #2d8cff;">🎉 Seu site de casamento foi criado!</h2>
      <p>Olá,</p>
      <p>Seu site de casamento foi criado com sucesso na plataforma MarriPlan!</p>
      <p>Acesse seu painel para personalizar e compartilhar com seus convidados.</p>
      <hr>
      <p style="font-size: 14px; color: #888;">Com carinho,<br>Equipe MarriPlan</p>
    </div>
  </body>
</html>
"""
EMAIL_WEDDING_SITE_UPDATE_SUBJECT = '💍 Seu site de casamento foi atualizado!'
EMAIL_WEDDING_SITE_UPDATE_BODY = """
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
      <h2 style="color: #2d8cff;">💍 Seu site de casamento foi atualizado!</h2>
      <p>Olá,</p>
      <p>As informações do seu site de casamento foram atualizadas.</p>
      <p>Confira as novidades acessando seu painel.</p>
      <hr>
      <p style="font-size: 14px; color: #888;">Com carinho,<br>Equipe MarriPlan</p>
    </div>
  </body>
</html>
"""
CHECKLIST_TASK_REMINDER_EMAIL_TEMPLATE = """
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
      <h2 style="color: #2d8cff;">⏰ Lembrete de tarefa do checklist</h2>
      <p>Olá <b>{email}</b>,</p>
      <p>Você tem uma tarefa do checklist com vencimento em 3 dias:</p>
      <p><b>{description}</b></p>
      <p>Não se esqueça de concluir a tarefa até <b>{due_date}</b>!</p>
      <hr>
      <p style="font-size: 14px; color: #888;">Com carinho,<br>Equipe MarriPlan</p>
    </div>
  </body>
</html>
"""
EMAIL_GIFT_PURCHASED_SUBJECT = '🎁 Presente comprado na sua lista!'
EMAIL_GIFT_PURCHASED_BODY = """
<html>
  <body style=\"font-family: Arial, sans-serif; color: #333;\">
    <div style=\"max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;\">
      <h2 style=\"color: #2d8cff;\">🎁 Um presente foi comprado!</h2>
      <p>Olá,</p>
      <p>O presente <b>{gift_name}</b> foi marcado como comprado na sua lista de presentes.</p>
      <p>Comprado por: <b>{purchased_by}</b></p>
      <p>Mensagem: <i>{message}</i></p>
      <hr>
      <p style=\"font-size: 14px; color: #888;\">Com carinho,<br>Equipe MarriPlan</p>
    </div>
  </body>
</html>
"""
EMAIL_GIFT_UNMARKED_SUBJECT = '🎁 Presente desmarcado como comprado'
EMAIL_GIFT_UNMARKED_BODY = """
<html>
  <body style=\"font-family: Arial, sans-serif; color: #333;\">
    <div style=\"max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;\">
      <h2 style=\"color: #2d8cff;\">🎁 Presente desmarcado como comprado</h2>
      <p>Olá,</p>
      <p>O presente <b>{gift_name}</b> foi desmarcado como comprado na sua lista de presentes.</p>
      <hr>
      <p style=\"font-size: 14px; color: #888;\">Com carinho,<br>Equipe MarriPlan</p>
    </div>
  </body>
</html>
"""
