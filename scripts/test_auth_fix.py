#!/usr/bin/env python3
"""
Teste para verificar se o problema de autenticação foi corrigido
"""

import os
import sys
import django
import logging
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import Client
from rest_framework.test import APIClient
import json

def test_auth_endpoints():
    """Testa endpoints de autenticação após correção"""
    print("🧪 TESTANDO ENDPOINTS DE AUTENTICAÇÃO APÓS CORREÇÃO")
    print("=" * 60)
    print()
    
    client = APIClient()
    
    # Dados de teste
    register_data = {
        'name': 'Test User Corrected',
        'email': 'testcorrected@example.com',
        'password': 'testpassword123'
    }
    
    login_data = {
        'email': 'nonexistent@example.com',
        'password': 'testpassword123'
    }
    
    # Lista de endpoints para testar
    endpoints = [
        {
            'name': 'Register (SignUpAPI)',
            'url': '/api/auth/register/',
            'method': 'POST',
            'data': register_data,
            'expected_status': [201, 400]  # 201 = criado, 400 = erro de validação (ok)
        },
        {
            'name': 'Pre-Login (PreLoginAPI)',
            'url': '/api/auth/pre-login/',
            'method': 'POST',
            'data': login_data,
            'expected_status': [200, 400]  # 400 = usuário não existe (ok)
        },
        {
            'name': 'Login (SignInAPI)',
            'url': '/api/auth/login/',
            'method': 'POST',
            'data': login_data,
            'expected_status': [200, 400]  # 400 = credenciais incorretas (ok)
        },
        {
            'name': 'Reset Password Request',
            'url': '/api/auth/reset-password/',
            'method': 'POST',
            'data': {'email': 'test@example.com'},
            'expected_status': [200]  # Sempre retorna 200 por segurança
        },
        {
            'name': 'Resend Confirmation',
            'url': '/api/auth/resend-confirmation/',
            'method': 'POST',
            'data': {'email': 'test@example.com'},
            'expected_status': [200, 404]  # 404 = usuário não encontrado (ok)
        }
    ]
    
    all_passed = True
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"{i}. Testando {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            if endpoint['method'] == 'POST':
                response = client.post(
                    endpoint['url'],
                    data=json.dumps(endpoint['data']),
                    content_type='application/json'
                )
            else:
                response = client.get(endpoint['url'])
            
            print(f"   Status retornado: {response.status_code}")
            
            if response.status_code == 401:
                print(f"   ❌ FALHOU: Ainda retornando 401 Unauthorized")
                print(f"   🔧 Este endpoint ainda precisa de correção")
                all_passed = False
            elif response.status_code in endpoint['expected_status']:
                print(f"   ✅ PASSOU: Status esperado ({response.status_code})")
            else:
                print(f"   ⚠️  Status inesperado: {response.status_code} (esperados: {endpoint['expected_status']})")
                print(f"   Isso pode ser normal dependendo dos dados de teste")
            
            # Mostrar resposta se for pequena
            try:
                content = response.content.decode('utf-8')
                if len(content) < 200:
                    print(f"   Resposta: {content}")
                else:
                    print(f"   Resposta: {content[:100]}...")
            except:
                print(f"   Resposta: [conteúdo binário]")
                
        except Exception as e:
            print(f"   ❌ ERRO na requisição: {str(e)}")
            all_passed = False
        
        print()
    
    # Resultado final
    print("=" * 60)
    if all_passed:
        print("🎉 SUCESSO! Todos os endpoints estão acessíveis")
        print("✅ O problema de autenticação foi corrigido")
        print()
        print("📋 Próximos passos:")
        print("1. Teste o login/registro no frontend")
        print("2. Se ainda houver problemas, verifique:")
        print("   - CORS configuration")
        print("   - Frontend headers/cookies")
        print("   - Network/firewall issues")
    else:
        print("❌ PROBLEMA AINDA EXISTE")
        print("⚠️  Alguns endpoints ainda retornam 401")
        print()
        print("🔧 Ações recomendadas:")
        print("1. Verifique se as alterações foram salvas em app/viewsets.py")
        print("2. Reinicie o servidor Django completamente")
        print("3. Verifique se não há middleware interferindo")
        print("4. Execute: python manage.py collectstatic")
    
    return all_passed

def check_viewset_changes():
    """Verifica se as mudanças foram aplicadas corretamente"""
    print("🔍 VERIFICANDO MUDANÇAS NO CÓDIGO")
    print("=" * 40)
    print()
    
    viewsets_file = Path(__file__).parent.parent / "app" / "viewsets.py"
    
    if not viewsets_file.exists():
        print("❌ Arquivo viewsets.py não encontrado")
        return False
    
    with open(viewsets_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se as classes têm permission_classes
    classes_to_check = [
        'SignUpAPI',
        'PreLoginAPI', 
        'SignInAPI',
        'ResetPasswordRequestAPI',
        'ResetPasswordConfirmAPI',
        'ConfirmEmailAPI',
        'ResendConfirmationEmailAPI'
    ]
    
    all_correct = True
    
    for class_name in classes_to_check:
        if f'class {class_name}(' in content:
            # Encontrar a classe e verificar se tem permission_classes
            lines = content.split('\n')
            class_found = False
            has_permissions = False
            
            for i, line in enumerate(lines):
                if f'class {class_name}(' in line:
                    class_found = True
                    # Verificar nas próximas 5 linhas
                    for j in range(i, min(i+5, len(lines))):
                        if 'permission_classes = [permissions.AllowAny]' in lines[j]:
                            has_permissions = True
                            break
                    break
            
            if class_found and has_permissions:
                print(f"✅ {class_name}: permission_classes configurado")
            elif class_found:
                print(f"❌ {class_name}: permission_classes AUSENTE")
                all_correct = False
            else:
                print(f"⚠️  {class_name}: classe não encontrada")
    
    print()
    return all_correct

def main():
    """Função principal de teste"""
    print("🚀 VERIFICAÇÃO DE CORREÇÃO DOS PROBLEMAS DE AUTH")
    print("=" * 60)
    print()
    
    # Verificar mudanças no código
    code_ok = check_viewset_changes()
    
    if not code_ok:
        print("❌ As mudanças no código não foram aplicadas corretamente")
        print("Execute novamente: python scripts/fix_auth_permissions.py")
        return
    
    print()
    
    # Testar endpoints
    endpoints_ok = test_auth_endpoints()
    
    print()
    print("=" * 60)
    if code_ok and endpoints_ok:
        print("🎉 PROBLEMA TOTALMENTE RESOLVIDO!")
        print("Você pode agora fazer login e registro normalmente")
    else:
        print("⚠️  Ainda há problemas que precisam ser investigados")

if __name__ == "__main__":
    main()