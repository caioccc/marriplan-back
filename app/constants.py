# app/constants.py

EMAIL_CONFIRMATION_HTML_TEMPLATE = """
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 24px;">
      <h2 style="color: #2d8cff;">Bem-vindo ao Marriplan!</h2>
      <p>Olá <b>{username}</b>,</p>
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
      <p>Olá <b>{username}</b>,</p>
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
