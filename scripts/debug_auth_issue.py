#!/usr/bin/env python3
"""
Script de Debug para Problemas de Autenticação
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
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from app.models import CustomUser
import json

logger = logging.getLogger(__name__)

def test_endpoints_accessibility():
    """Testa acessibilidade dos endpoints de autenticação"""
    print("=== TESTE DE ACESSIBILIDADE DOS ENDPOINTS ===\n")
    
    client = APIClient()
    
    # Dados de teste
    test_data = {
        'email': 'test@example.com',
        'password': 'testpassword123'
    }
    
    register_data = {
        'name': 'Test User',
        'email': 'newuser@example.com',
        'password': 'testpassword123'
    }
    
    endpoints_to_test = [
        {
            'name': 'Pre-Login',
            'url': '/api/auth/pre-login/',
            'method': 'POST',
            'data': test_data,
            'should_be_public': True
        },
        {
            'name': 'Register',
            'url': '/api/auth/register/',
            'method': 'POST',
            'data': register_data,
            'should_be_public': True
        },
        {
            'name': 'Login',
            'url': '/api/auth/login/',
            'method': 'POST',
            'data': test_data,
            'should_be_public': True
        }
    ]
    
    for endpoint in endpoints_to_test:
        print(f"🔍 Testando {endpoint['name']}: {endpoint['url']}")
        
        try:
            if endpoint['method'] == 'POST':
                response = client.post(
                    endpoint['url'], 
                    data=json.dumps(endpoint['data']),
                    content_type='application/json'
                )
            else:
                response = client.get(endpoint['url'])
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 401:
                print(f"   ❌ PROBLEMA: Endpoint retornando 401 Unauthorized")
                print(f"   Isso indica que o endpoint está requerendo autenticação quando deveria ser público")
            elif response.status_code in [200, 201, 400]:
                print(f"   ✅ OK: Endpoint acessível (status {response.status_code})")
            else:
                print(f"   ⚠️  Status inesperado: {response.status_code}")
            
            try:
                content = response.content.decode('utf-8')
                if content:
                    print(f"   Resposta: {content[:200]}...")
            except:
                print(f"   Resposta: {response.content}")
                
        except Exception as e:
            print(f"   ❌ ERRO na requisição: {str(e)}")
        
        print()

def check_rest_framework_settings():
    """Verifica configurações do Django REST Framework"""
    print("=== VERIFICAÇÃO DAS CONFIGURAÇÕES DRF ===\n")
    
    from django.conf import settings
    
    # Verificar configurações de permissão
    drf_settings = getattr(settings, 'REST_FRAMEWORK', {})
    
    print(f"DEFAULT_PERMISSION_CLASSES: {drf_settings.get('DEFAULT_PERMISSION_CLASSES', 'Não definido')}")
    print(f"DEFAULT_AUTHENTICATION_CLASSES: {drf_settings.get('DEFAULT_AUTHENTICATION_CLASSES', 'Não definido')}")
    
    # Verificar se permissões estão muito restritivas
    default_permissions = drf_settings.get('DEFAULT_PERMISSION_CLASSES', ())
    
    if 'rest_framework.permissions.IsAuthenticated' in default_permissions:
        print("❌ PROBLEMA ENCONTRADO: DEFAULT_PERMISSION_CLASSES inclui IsAuthenticated")
        print("   Isso força TODOS os endpoints a requererem autenticação por padrão")
        print("   Endpoints públicos (register, login) devem sobrescrever isso explicitamente")
    else:
        print("✅ Configuração de permissões parece OK")
    
    print()

def check_viewset_permissions():
    """Verifica permissões específicas dos ViewSets"""
    print("=== VERIFICAÇÃO DE PERMISSÕES DOS VIEWSETS ===\n")
    
    from app.viewsets import SignUpAPI, PreLoginAPI, SignInAPI
    
    viewsets_to_check = [
        ('SignUpAPI', SignUpAPI),
        ('PreLoginAPI', PreLoginAPI),
        ('SignInAPI', SignInAPI)
    ]
    
    for name, viewset_class in viewsets_to_check:
        print(f"🔍 Verificando {name}:")
        
        # Verificar se tem permission_classes definido
        if hasattr(viewset_class, 'permission_classes'):
            permissions = viewset_class.permission_classes
            print(f"   permission_classes: {permissions}")
            
            # Verificar se permite acesso anônimo
            from rest_framework.permissions import AllowAny
            if AllowAny in permissions:
                print(f"   ✅ Permite acesso anônimo (AllowAny)")
            else:
                print(f"   ❌ PROBLEMA: Não permite explicitamente acesso anônimo")
                print(f"   Recomendação: Adicionar AllowAny às permission_classes")
        else:
            print(f"   ⚠️  permission_classes não definido - usando configuração global")
        
        print()

def test_user_creation():
    """Testa criação de usuário diretamente"""
    print("=== TESTE DE CRIAÇÃO DE USUÁRIO ===\n")
    
    try:
        # Limpar usuários de teste existentes
        User = get_user_model()
        User.objects.filter(email='testuser@example.com').delete()
        
        # Tentar criar usuário
        user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123'
        )
        
        print(f"✅ Usuário criado com sucesso: {user.username} ({user.email})")
        print(f"   is_active: {user.is_active}")
        print(f"   is_email_confirmed: {getattr(user, 'is_email_confirmed', 'N/A')}")
        
        # Testar autenticação
        from django.contrib.auth import authenticate
        auth_user = authenticate(username=user.username, password='testpassword123')
        
        if auth_user:
            print(f"✅ Autenticação funcionando")
        else:
            print(f"❌ PROBLEMA: Autenticação falhou")
        
        # Limpar
        user.delete()
        
    except Exception as e:
        print(f"❌ ERRO na criação de usuário: {str(e)}")
    
    print()

def check_middleware():
    """Verifica middleware que pode estar interferindo"""
    print("=== VERIFICAÇÃO DE MIDDLEWARE ===\n")
    
    from django.conf import settings
    
    middleware = settings.MIDDLEWARE
    
    print("Middleware configurado:")
    for i, mw in enumerate(middleware, 1):
        print(f"   {i}. {mw}")
    
    # Verificar middleware problemático
    problematic_middleware = [
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware'
    ]
    
    for mw in problematic_middleware:
        if mw in middleware:
            print(f"⚠️  {mw} está ativo - pode afetar APIs")
    
    print()

def test_direct_serializer():
    """Testa serializers diretamente"""
    print("=== TESTE DIRETO DOS SERIALIZERS ===\n")
    
    from app.serializers import RegisterSerializer, PreLoginSerializer
    
    # Testar RegisterSerializer
    print("🔍 Testando RegisterSerializer:")
    register_data = {
        'name': 'Test User',
        'email': 'serializer_test@example.com',
        'password': 'testpassword123'
    }
    
    try:
        serializer = RegisterSerializer(data=register_data)
        if serializer.is_valid():
            print("   ✅ RegisterSerializer válido")
            # user = serializer.save()  # Não salvar realmente
            # print(f"   Usuário seria criado: {user.username}")
        else:
            print(f"   ❌ RegisterSerializer inválido: {serializer.errors}")
    except Exception as e:
        print(f"   ❌ ERRO no RegisterSerializer: {str(e)}")
    
    # Testar PreLoginSerializer
    print("\n🔍 Testando PreLoginSerializer:")
    login_data = {
        'email': 'nonexistent@example.com',
        'password': 'testpassword123'
    }
    
    try:
        serializer = PreLoginSerializer(data=login_data)
        serializer.is_valid()  # Esperamos que falhe para usuário inexistente
        print("   ✅ PreLoginSerializer processando corretamente")
    except Exception as e:
        print(f"   ❌ ERRO no PreLoginSerializer: {str(e)}")
    
    print()

def main():
    """Função principal de debug"""
    print("🚨 SCRIPT DE DEBUG - PROBLEMAS DE AUTENTICAÇÃO")
    print("=" * 60)
    print()
    
    # Executar todos os testes
    check_rest_framework_settings()
    check_viewset_permissions()
    check_middleware()
    test_direct_serializer()
    test_user_creation()
    test_endpoints_accessibility()
    
    print("=" * 60)
    print("🔧 RECOMENDAÇÕES DE CORREÇÃO:")
    print()
    print("1. Verificar se os ViewSets têm permission_classes = [permissions.AllowAny]")
    print("2. Confirmar que REST_FRAMEWORK settings não força IsAuthenticated globalmente")
    print("3. Verificar se middleware não está interferindo")
    print("4. Testar com diferentes clientes (Postman, curl)")
    print()
    print("Para corrigir, execute: python scripts/fix_auth_permissions.py")

if __name__ == "__main__":
    main()