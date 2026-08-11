#!/usr/bin/env python3
"""
Validazione dell'ambiente di sviluppo per MobileRun Tester
"""

import sys
import os

def test_imports():
    """Testa che le dipendenze chiave siano importabili"""
    try:
        import yaml
        print("✓ PyYAML importato correttamente")
    except ImportError as e:
        print(f"✗ Errore import PyYAML: {e}")
        return False
    
    try:
        from PIL import Image
        print("✓ Pillow importato correttamente")
    except ImportError as e:
        print(f"✗ Errore import Pillow: {e}")
        return False
        
    try:
        import imagehash
        print("✓ imagehash importato correttamente")
    except ImportError as e:
        print(f"✗ Errore import imagehash: {e}")
        return False
    
    # Test project modules
    try:
        from mobilerun_tester.core import adb_engine, vision_engine, server_manager, logger
        from mobilerun_tester.runner import test_runner, report_generator
        from mobilerun_tester.cli import main
        print("✓ Moduli del progetto importati correttamente")
    except Exception as e:
        print(f"✗ Errore import moduli progetto: {e}")
        return False
    
    return True

def test_scenario_loading():
    """Testa il caricamento dello scenario di esempio"""
    try:
        import yaml
        scenario_path = os.path.join(
            os.path.dirname(__file__), 
            'scenarios', 
            'login_flow.yaml'
        )
        with open(scenario_path, 'r', encoding='utf-8') as f:
            scenario = yaml.safe_load(f)
        
        print("✓ Scenario di login caricato correttamente")
        print(f"  Nome: {scenario.get('name')}")
        print(f"  Passi: {len(scenario.get('steps', []))}")
        return True
    except Exception as e:
        print(f"✗ Errore caricamento scenario: {e}")
        return False

def main():
    print("=" * 50)
    print("VALIDAZIONE AMBIENTE SVILUPPO MOBILERUN TESTER")
    print("=" * 50)
    
    success = True
    success &= test_imports()
    print()
    success &= test_scenario_loading()
    
    print()
    if success:
        print("🎉 VALIDAZIONE COMPLETATA - Ambiente pronto!")
        return 0
    else:
        print("❌ VALIDAZIONE FALLITA - Controllare gli errori sopra")
        return 1

if __name__ == "__main__":
    sys.exit(main())