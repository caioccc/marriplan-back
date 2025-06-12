#!/usr/bin/env python3
"""
Validação de Integração Completa - Todas as Fases do Sistema Marriplan
Este script executa todos os scripts de validação e gera um relatório consolidado.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class IntegrationValidationResult:
    """Resultado consolidado da validação de integração"""
    def __init__(self):
        self.phase_results = {}
        self.total_tests = 0
        self.total_passed = 0
        self.total_failed = 0
        self.execution_time = 0
        self.start_time = None
        self.end_time = None

    def add_phase_result(self, phase_name: str, success: bool, output: str):
        """Adiciona resultado de uma fase"""
        self.phase_results[phase_name] = {
            'success': success,
            'output': output,
            'timestamp': datetime.now()
        }

    def calculate_totals(self):
        """Calcula totais a partir dos outputs"""
        for phase_name, result in self.phase_results.items():
            output = result['output']

            # Extrair estatísticas do output (formato: ✅ Sucessos: X, ❌ Falhas: Y)
            lines = output.split('\n')
            for line in lines:
                if '✅ Sucessos:' in line and '❌ Falhas:' in line:
                    try:
                        # Extrair números
                        parts = line.split('✅ Sucessos:')[1].split('❌ Falhas:')
                        passed = int(parts[0].strip())
                        failed = int(parts[1].strip())

                        self.total_passed += passed
                        self.total_failed += failed
                        self.total_tests += (passed + failed)
                        break
                    except (ValueError, IndexError):
                        continue

    def print_final_report(self):
        """Imprime relatório final consolidado"""
        print("\n" + "="*80)
        print("RELATÓRIO DE VALIDAÇÃO COMPLETA DO SISTEMA Marriplan")
        print("="*80)

        print(f"\n📊 **RESUMO EXECUTIVO**")
        print(f"Período de execução: {self.start_time.strftime('%d/%m/%Y %H:%M:%S')} - {self.end_time.strftime('%H:%M:%S')}")
        print(f"Tempo total: {self.execution_time:.2f} segundos")
        print(f"Fases testadas: {len(self.phase_results)}")

        print(f"\n📈 **ESTATÍSTICAS GLOBAIS**")
        print(f"Total de testes executados: {self.total_tests}")
        print(f"✅ Testes aprovados: {self.total_passed}")
        print(f"❌ Testes falharam: {self.total_failed}")

        if self.total_tests > 0:
            success_rate = (self.total_passed / self.total_tests) * 100
            print(f"📊 Taxa de sucesso: {success_rate:.1f}%")

        print(f"\n🔍 **RESULTADOS POR FASE**")

        for phase_name, result in self.phase_results.items():
            status_icon = "✅" if result['success'] else "❌"
            status_text = "APROVADA" if result['success'] else "FALHOU"

            print(f"\n{status_icon} **{phase_name}**: {status_text}")

            # Extrair resumo do output
            output_lines = result['output'].split('\n')
            for line in output_lines:
                if '✅ Sucessos:' in line and '❌ Falhas:' in line:
                    print(f"   {line.strip()}")
                    break

        print(f"\n🎯 **AVALIAÇÃO FINAL**")

        failed_phases = [name for name, result in self.phase_results.items() if not result['success']]

        if not failed_phases:
            print("🎉 **SISTEMA COMPLETAMENTE VALIDADO!**")
            print("✨ Todas as fases passaram na validação")
            print("🚀 O sistema está pronto para produção")
        else:
            print(f"⚠️  **{len(failed_phases)} FASE(S) COM PROBLEMAS:**")
            for phase in failed_phases:
                print(f"   • {phase}")
            print("\n🔧 Recomendação: Revisar e corrigir os problemas identificados")

        print(f"\n📋 **PRÓXIMOS PASSOS**")
        if not failed_phases:
            print("1. ✅ Sistema validado - pode prosseguir para deploy")
            print("2. 📚 Documentar configurações finais")
            print("3. 🔄 Configurar monitoramento em produção")
        else:
            print("1. 🔧 Corrigir problemas nas fases com falha")
            print("2. 🔄 Re-executar validação após correções")
            print("3. 📝 Atualizar documentação conforme necessário")

        print("\n" + "="*80)

def run_validation_script(script_path: Path) -> tuple[bool, str]:
    """Executa um script de validação e retorna resultado"""
    try:
        print(f"Executando: {script_path.name}...")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos timeout
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr

        return success, output

    except subprocess.TimeoutExpired:
        return False, "Timeout: Script demorou mais de 5 minutos para executar"
    except Exception as e:
        return False, f"Erro na execução: {str(e)}"

def main():
    """Função principal de validação de integração"""
    print("Iniciando validação de integração completa do Sistema Marriplan...")
    print("Este processo pode levar alguns minutos...\n")

    result = IntegrationValidationResult()
    result.start_time = datetime.now()

    # Scripts de validação na ordem das fases
    scripts_dir = Path(__file__).parent

    validation_scripts = [
        ("Fase 1 - Sistema Q&A", "validate_phase1_qa_system.py"),
        ("Fase 2 - ETL e Embeddings", "validate_phase2_etl_embedding.py"),
        ("Fase 3 - Busca e Reranking", "validate_phase3_search_reranking.py"),
        ("Fase 4 - Detecção de Intenção", "validate_phase4_intent_detection.py"),
        ("Fase 5 - i18n e Legacy", "validate_phase5_i18n_legacy.py"),
        ("Fase 6 - Agentes Avançados", "validate_phase6_advanced_agents.py")
    ]

    print("📋 Fases a serem validadas:")
    for i, (phase_name, script_name) in enumerate(validation_scripts, 1):
        print(f"   {i}. {phase_name}")
    print()

    # Executar cada script de validação
    for phase_name, script_name in validation_scripts:
        script_path = scripts_dir / script_name

        if not script_path.exists():
            print(f"❌ Script não encontrado: {script_name}")
            result.add_phase_result(phase_name, False, f"Script {script_name} não encontrado")
            continue

        print(f"🔄 Executando validação: {phase_name}")
        success, output = run_validation_script(script_path)

        result.add_phase_result(phase_name, success, output)

        # Mostrar resultado imediato
        status = "✅ APROVADA" if success else "❌ FALHOU"
        print(f"   Resultado: {status}")

        # Mostrar erros se houver
        if not success:
            lines = output.split('\n')
            error_lines = [line for line in lines if '❌' in line]
            if error_lines:
                print(f"   Primeiros erros:")
                for error_line in error_lines[:3]:  # Mostrar só os primeiros 3 erros
                    print(f"     {error_line.strip()}")
                if len(error_lines) > 3:
                    print(f"     ... e mais {len(error_lines) - 3} erro(s)")
        print()

    result.end_time = datetime.now()
    result.execution_time = (result.end_time - result.start_time).total_seconds()

    # Calcular totais
    result.calculate_totals()

    # Gerar relatório final
    result.print_final_report()

    # Salvar relatório detalhado
    save_detailed_report(result)

    # Retornar código de saída
    all_passed = all(result['success'] for result in result.phase_results.values())
    return 0 if all_passed else 1

def save_detailed_report(result: IntegrationValidationResult):
    """Salva relatório detalhado em arquivo"""
    try:
        reports_dir = Path(__file__).parent.parent / "docs"
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Relatório de Validação Completa - Sistema Marriplan\n\n")
            f.write(f"**Data:** {result.start_time.strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"**Duração:** {result.execution_time:.2f} segundos\n\n")

            f.write("## Resumo Executivo\n\n")
            f.write(f"- **Total de testes:** {result.total_tests}\n")
            f.write(f"- **Aprovados:** {result.total_passed}\n")
            f.write(f"- **Falharam:** {result.total_failed}\n")

            if result.total_tests > 0:
                success_rate = (result.total_passed / result.total_tests) * 100
                f.write(f"- **Taxa de sucesso:** {success_rate:.1f}%\n")

            f.write("\n## Resultados por Fase\n\n")

            for phase_name, phase_result in result.phase_results.items():
                status = "✅ APROVADA" if phase_result['success'] else "❌ FALHOU"
                f.write(f"### {phase_name}: {status}\n\n")

                # Adicionar output formatado
                f.write("```\n")
                f.write(phase_result['output'])
                f.write("\n```\n\n")

        print(f"\n📄 Relatório detalhado salvo em: {report_file}")

    except Exception as e:
        print(f"\n⚠️  Erro ao salvar relatório: {e}")

def validate_environment():
    """Valida ambiente antes de executar testes"""
    print("🔍 Validando ambiente de execução...")

    # Verificar Python
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ Python {python_version.major}.{python_version.minor} detectado. Requerido: Python 3.8+")
        return False

    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Verificar Django
    try:
        import django
        print(f"✅ Django {django.get_version()}")
    except ImportError:
        print("❌ Django não encontrado")
        return False

    # Verificar diretório do projeto
    project_root = Path(__file__).parent.parent
    required_dirs = [
        "app",
        "app/core",
        "app/core/agents",
        "app/core/services",
        "app/core/i18n"
    ]

    for req_dir in required_dirs:
        dir_path = project_root / req_dir
        if not dir_path.exists():
            print(f"❌ Diretório requerido não encontrado: {req_dir}")
            return False

    print("✅ Estrutura do projeto validada")
    print()

    return True

if __name__ == "__main__":
    print("🚀 Sistema de Validação Completa - Marriplan")
    print("=" * 50)
    print()

    # Validar ambiente
    if not validate_environment():
        print("❌ Ambiente inválido. Corrija os problemas e tente novamente.")
        sys.exit(1)

    # Executar validação completa
    exit_code = main()

    print(f"\n🏁 Validação completa finalizada com código: {exit_code}")
    sys.exit(exit_code)