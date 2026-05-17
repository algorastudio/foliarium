#!/usr/bin/env python3
"""
generate_key.py — Generatore di chiave HMAC-SHA256 per Foliarium License Manager

Uso:
  python generate_key.py                    # Menu interattivo
  python generate_key.py --save-exe-dir     # Salva automaticamente in EXE_DIR
  python generate_key.py --save-base-dir    # Salva automaticamente in BASE_DIR
  python generate_key.py --env-var          # Stampa il valore per variabile d'ambiente
"""

import secrets
import argparse
import textwrap
from pathlib import Path

try:
    from app_paths import EXE_DIR, BASE_DIR
except ImportError:
    # Fallback se app_paths non è disponibile
    BASE_DIR = Path(__file__).parent
    EXE_DIR = BASE_DIR


def generate_hmac_key(size_bytes: int = 32) -> bytes:
    """
    Genera una chiave casuale sicura per HMAC-SHA256.

    Args:
        size_bytes: Lunghezza della chiave in byte (default: 32 = 256 bit)

    Returns:
        Chiave casuale come bytes
    """
    return secrets.token_bytes(size_bytes)


def print_security_warning():
    """Stampa avvertenza di sicurezza."""
    warning = textwrap.dedent("""
    ⚠️  AVVERTENZA DI SICUREZZA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    La chiave HMAC-SHA256 è CRITICA per la sicurezza del sistema di licenze.

    ✅ COSA FARE:
       • Mantieni la chiave SEGRETISSIMA
       • NON commitare foliarium.key su Git
       • NON condividere la chiave via email/chat
       • Usa una variabile d'ambiente in produzione
       • Genera una nuova chiave per ogni ambiente (dev, staging, prod)
       • Fai un backup sicuro della chiave

    ❌ NON FARE:
       • Non hardcodare la chiave nel codice
       • Non mettere foliarium.key nei backup automatici
       • Non usare la stessa chiave per più installazioni
       • Non perdere la chiave originale (non è recuperabile)

    ⚡ SE COMPROMESSA:
       • Tutte le licenze (.license) diventano inaffidabili
       • Regene una nuova chiave e comunica ai clienti

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)
    print(warning)


def save_key_to_file(key_bytes: bytes, file_path: Path) -> bool:
    """
    Salva la chiave in un file binario.

    Returns:
        True se successo, False altrimenti
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(key_bytes)
        # Imposta permessi stretti su Unix (ignora su Windows)
        try:
            file_path.chmod(0o600)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"❌ Errore durante il salvataggio: {e}")
        return False


def interactive_mode():
    """Modalità interattiva con menu."""
    print("\n" + "="*80)
    print("GENERATORE CHIAVE FOLIARIUM LICENSE")
    print("="*80)

    print_security_warning()

    # Genera la chiave
    key = generate_hmac_key()
    key_hex = key.hex()

    print("\n✅ Chiave HMAC-SHA256 generata (32 byte):")
    print(f"\n   HEX: {key_hex}")
    print(f"   Base64: {__import__('base64').b64encode(key).decode()}")

    print("\n" + "-"*80)
    print("DOVE SALVARE IL FILE?")
    print("-"*80)

    options = {
        "1": ("Accanto a Foliarium.exe (EXE_DIR)", EXE_DIR),
        "2": ("In BASE_DIR (cartella progetto)", BASE_DIR),
        "3": ("Custom (specifica percorso)", None),
        "4": ("Solo mostra chiave (non salvare)", None),
    }

    for key_opt, (desc, _) in options.items():
        print(f"  {key_opt}) {desc}")

    choice = input("\nScelta [1-4]: ").strip()

    if choice == "1":
        target_path = EXE_DIR / "foliarium.key"
    elif choice == "2":
        target_path = BASE_DIR / "foliarium.key"
    elif choice == "3":
        custom = input("Inserisci percorso completo: ").strip()
        target_path = Path(custom)
    elif choice == "4":
        print("\n✅ Chiave generata (non salvata).")
        print("   Per usarla, imposta la variabile d'ambiente:")
        print(f"   FOLIARIUM_LICENSE_KEY={key_hex}")
        return
    else:
        print("❌ Scelta non valida.")
        return

    # Conferma salvataggio
    print(f"\n📝 Percorso target: {target_path}")
    confirm = input("Salvare il file? [S/n]: ").strip().lower()

    if confirm in ("s", "si", "sì", "yes", "y", ""):
        if save_key_to_file(key, target_path):
            print(f"\n✅ File salvato: {target_path}")
            print(f"   Permessi: 0o600 (solo lettura proprietario)")
            print("\n⚡ Ricorda:")
            print("   • Fai un backup sicuro di questo file")
            print("   • Non commitarlo su Git")
            print("   • Se perso, non è recuperabile")
    else:
        print("Operazione annullata.")


def main():
    parser = argparse.ArgumentParser(
        description="Generatore chiave HMAC-SHA256 per Foliarium License Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--save-exe-dir",
        action="store_true",
        help="Salva automaticamente in EXE_DIR (accanto all'eseguibile)",
    )
    parser.add_argument(
        "--save-base-dir",
        action="store_true",
        help="Salva automaticamente in BASE_DIR (cartella progetto)",
    )
    parser.add_argument(
        "--env-var",
        action="store_true",
        help="Stampa solo il valore HEX per variabile d'ambiente (non salva)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=32,
        help="Lunghezza chiave in byte (default: 32 = 256 bit)",
    )

    args = parser.parse_args()

    # Genera la chiave
    key = generate_hmac_key(args.size)
    key_hex = key.hex()

    # Modalità --env-var
    if args.env_var:
        print(key_hex)
        return

    # Stampa warning di sicurezza
    if args.save_exe_dir or args.save_base_dir:
        print("⚠️  Generando chiave HMAC-SHA256...")
    else:
        print_security_warning()

    # Modalità --save-exe-dir
    if args.save_exe_dir:
        target_path = EXE_DIR / "foliarium.key"
        if save_key_to_file(key, target_path):
            print(f"✅ Chiave salvata: {target_path}")
        return

    # Modalità --save-base-dir
    if args.save_base_dir:
        target_path = BASE_DIR / "foliarium.key"
        if save_key_to_file(key, target_path):
            print(f"✅ Chiave salvata: {target_path}")
        return

    # Modalità interattiva (default)
    interactive_mode()


if __name__ == "__main__":
    main()
