#!/usr/bin/env python3
"""
Script para Corrigir Problemas de Permissões de Autenticação
"""

import os
import sys
from pathlib import Path

def fix_viewsets_permissions():
    """Corrige permissões nos ViewSets de autenticação"""
    print("🔧 Corrigindo permissões nos ViewSets...")
    
    viewsets_file = Path(__file__).parent.parent / "app" / "viewsets.py"
    
    if not viewsets_file.exists():
        print(f"❌ Arquivo não encontrado: {viewsets_file}")
        return False
    
    # Ler arquivo atual
    with open(viewsets_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se já tem as permissões corretas
    if 'permission_classes = [permissions.AllowAny]' in content:
        print("✅ Permissões já estão corretas nos ViewSets")
        return True
    
    # Encontrar e corrigir as classes que precisam de acesso público
    corrections = []
    
    # SignUpAPI
    if 'class SignUpAPI(' in content and 'permission_classes = [permissions.AllowAny]' not in content:
        # Encontrar a posição da classe
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Adicionar permission_classes após a definição da classe
            if line.strip().startswith('class SignUpAPI(') and i + 1 < len(lines):
                # Verificar se não já existe
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('SignUpAPI')
            
            elif line.strip().startswith('class PreLoginAPI(') and i + 1 < len(lines):
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('PreLoginAPI')
            
            elif line.strip().startswith('class SignInAPI(') and i + 1 < len(lines):
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('SignInAPI')
            
            elif line.strip().startswith('class ResetPasswordRequestAPI(') and i + 1 < len(lines):
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('ResetPasswordRequestAPI')
            
            elif line.strip().startswith('class ResetPasswordConfirmAPI(') and i + 1 < len(lines):
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('ResetPasswordConfirmAPI')
            
            elif line.strip().startswith('class ConfirmEmailAPI(') and i + 1 < len(lines):
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('ConfirmEmailAPI')
            
            elif line.strip().startswith('class ResendConfirmationEmailAPI(') and i + 1 < len(lines):
                next_few_lines = '\n'.join(lines[i:i+5])
                if 'permission_classes' not in next_few_lines:
                    new_lines.append('    permission_classes = [permissions.AllowAny]')
                    corrections.append('ResendConfirmationEmailAPI')
        
        # Escrever arquivo corrigido
        corrected_content = '\n'.join(new_lines)
        
        # Fazer backup
        backup_file = viewsets_file.with_suffix('.py.backup')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📁 Backup criado: {backup_file}")
        
        # Escrever correção
        with open(viewsets_file, 'w', encoding='utf-8') as f:
            f.write(corrected_content)
        
        if corrections:
            print(f"✅ Permissões corrigidas para: {', '.join(corrections)}")
        else:
            print("ℹ️  Nenhuma correção necessária")
        
        return True
    
    print("✅ ViewSets já estão corretos")
    return True

def create_test_endpoint():
    """Cria endpoint de teste para verificar se o problema foi resolvido"""
    print("🧪 Criando endpoint de teste...")
    
    test_file = Path(__file__).parent.parent / "scripts" / "test_auth_endpoints.py"
    
    test_code = '''#!/usr/bin/env python3
"""
Teste dos Endpoints de Autenticação Corrigidos
"""

import requests
import json

def test_endpoints():
    """Testa os endpoints de autenticação"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testando endpoints de autenticação...")
    print()
    
    # Teste 1: Register
    print("1. Testando /auth/register/")
    register_data = {
        "name": "Test User",
        "email": "test_user_fix@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/register/",
            json=register_data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ❌ Ainda retornando 401 - problema não resolvido")
        elif response.status_code in [201, 400]:
            print("   ✅ Endpoint acessível")
        print(f"   Resposta: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 2: Pre-login
    print("2. Testando /auth/pre-login/")
    login_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/pre-login/",
            json=login_data,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ❌ Ainda retornando 401 - problema não resolvido")
        elif response.status_code in [200, 400]:
            print("   ✅ Endpoint acessível")
        print(f"   Resposta: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    print("🏁 Teste concluído")

if __name__ == "__main__":
    test_endpoints()
'''
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    print(f"✅ Arquivo de teste criado: {test_file}")
    print("   Execute: python scripts/test_auth_endpoints.py")
    
    return True

def show_manual_fix_instructions():
    """Mostra instruções para correção manual"""
    print("\n" + "="*60)
    print("📋 INSTRUÇÕES PARA CORREÇÃO MANUAL")
    print("="*60)
    print()
    print("Se o script automático não funcionou, siga estes passos:")
    print()
    print("1. Abra o arquivo: app/viewsets.py")
    print()
    print("2. Para cada uma das classes abaixo, adicione a linha:")
    print("   permission_classes = [permissions.AllowAny]")
    print()
    print("   Classes que precisam desta correção:")
    print("   - SignUpAPI")
    print("   - PreLoginAPI") 
    print("   - SignInAPI")
    print("   - ResetPasswordRequestAPI")
    print("   - ResetPasswordConfirmAPI")
    print("   - ConfirmEmailAPI")
    print("   - ResendConfirmationEmailAPI")
    print()
    print("3. Exemplo de como deve ficar:")
    print()
    print("   class SignUpAPI(generics.GenericAPIView):")
    print("       permission_classes = [permissions.AllowAny]  # <- ADICIONAR ESTA LINHA")
    print("       serializer_class = RegisterSerializer")
    print("       ...")
    print()
    print("4. Salve o arquivo e reinicie o servidor Django")
    print()
    print("5. Teste novamente o login/registro")

def main():
    """Função principal de correção"""
    print("🚀 SCRIPT DE CORREÇÃO - PROBLEMAS DE AUTENTICAÇÃO")
    print("=" * 60)
    print()
    
    try:
        # Executar correções
        success = fix_viewsets_permissions()
        
        if success:
            create_test_endpoint()
            print("\n✅ CORREÇÕES APLICADAS COM SUCESSO!")
            print()
            print("📋 PRÓXIMOS PASSOS:")
            print("1. Reinicie o servidor Django:")
            print("   python manage.py runserver")
            print()
            print("2. Teste os endpoints:")
            print("   python scripts/test_auth_endpoints.py")
            print()
            print("3. Ou teste manualmente no frontend")
        else:
            show_manual_fix_instructions()
    
    except Exception as e:
        print(f"❌ Erro durante a correção: {e}")
        show_manual_fix_instructions()

if __name__ == "__main__":
    main()