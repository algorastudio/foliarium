#!/usr/bin/env python3
"""
generate_license.py — Utility CLI per la gestione delle licenze Foliarium

Comandi disponibili:
  generate   Genera un nuovo file .license per un cliente
  inspect    Mostra le informazioni di un file .license esistente
  fingerprint  Mostra il fingerprint hardware del computer corrente

Esempi:
  python generate_license.py generate --to "Comune di Firenze" --type standard --seats 2 --expiry 2027-12-31 --out savona.license

  python generate_license.py generate \\
      --to "Comune di Albenga" \\
      --type standard \\
      --seats 1 \\
      --hardware a1b2c3d4e5f6g7h8 \\
      --out albenga.license

  python generate_license.py inspect savona.license

  python generate_license.py fingerprint
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_generate(args: argparse.Namespace) -> None:
    from foliarium.core.services.license import generate_license, get_hardware_fingerprint

    hw_id = args.hardware
    if args.bind_local:
        hw_id = get_hardware_fingerprint()
        print(f"  Hardware ID di questo computer: {hw_id}")

    content = generate_license(
        licensed_to=args.to,
        license_type=args.type,
        max_seats=args.seats,
        expiry_date=args.expiry,
        hardware_id=hw_id,
    )

    out_path = Path(args.out)
    out_path.write_text(content, encoding="utf-8")

    print(f"\n{'='*55}")
    print(f" Licenza generata: {out_path}")
    print(f"{'='*55}")
    _print_license_info(json.loads(content))
    print(f"\nDistribuire il file '{out_path}' al cliente.\n")


def cmd_inspect(args: argparse.Namespace) -> None:
    from foliarium.core.services.license import _validate_file, get_hardware_fingerprint

    path = args.file
    if not Path(path).exists():
        print(f"ERRORE: file non trovato: {path}", file=sys.stderr)
        sys.exit(1)

    info = _validate_file(path)
    current_fp = get_hardware_fingerprint()

    print(f"\n{'='*55}")
    print(f" Ispezione: {path}")
    print(f"{'='*55}")
    print(f"  Valida         : {'✔  SÌ' if info.is_valid else '✘  NO — ' + info.error_message}")
    print(f"  Intestata a    : {info.licensed_to or '—'}")
    print(f"  Tipo           : {info.license_type}")
    print(f"  Max seat       : {info.max_seats}")
    if info.expiry_date:
        days = info.days_to_expiry()
        status = "SCADUTA" if days < 0 else f"tra {days} giorni"
        print(f"  Scadenza       : {info.expiry_date.strftime('%d/%m/%Y')} ({status})")
    else:
        print(f"  Scadenza       : Perpetua")
    print(f"  Hardware ID    : {info.hardware_id or 'Qualsiasi (floating)'}")
    print(f"  Emessa il      : {info.issued_at.strftime('%d/%m/%Y')}")
    print(f"  ID computer    : {current_fp}")
    if info.hardware_id:
        match = "✔ corrisponde" if info.hardware_id == current_fp else "✘ NON corrisponde"
        print(f"  Compatibilità  : {match}")
    print()


def cmd_fingerprint(_args: argparse.Namespace) -> None:
    from foliarium.core.services.license import get_hardware_fingerprint
    import socket
    import uuid

    fp = get_hardware_fingerprint()
    mac = uuid.getnode()
    host = socket.gethostname()

    print(f"\n{'='*55}")
    print(f" Fingerprint hardware di questo computer")
    print(f"{'='*55}")
    print(f"  Hostname       : {host}")
    print(f"  MAC address    : {':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(40, -1, -8))}")
    print(f"  Fingerprint    : {fp}")
    print(f"\nUsare questo fingerprint con --hardware durante la generazione")
    print(f"di una licenza vincolata a questo specifico computer.\n")


def _print_license_info(data: dict) -> None:
    type_labels = {"demo": "Demo", "standard": "Standard", "enterprise": "Enterprise"}
    print(f"  Intestata a    : {data.get('licensed_to', '—')}")
    print(f"  Tipo           : {type_labels.get(data.get('license_type', ''), data.get('license_type', ''))}")
    print(f"  Max seat       : {data.get('max_seats', 1)}")
    expiry = data.get('expiry_date')
    print(f"  Scadenza       : {expiry if expiry else 'Perpetua'}")
    hw = data.get('hardware_id')
    print(f"  Hardware ID    : {hw if hw else 'Qualsiasi (floating)'}")
    print(f"  Emessa il      : {data.get('issued_at', '—')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gestione licenze Foliarium",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- generate ---
    p_gen = sub.add_parser("generate", help="Genera un nuovo file .license")
    p_gen.add_argument("--to",       required=True, metavar="NOME",
                       help="Nome del licenziatario (es. 'Comune di Firenze')")
    p_gen.add_argument("--type",     default="standard",
                       choices=["demo", "standard", "enterprise"],
                       help="Tipo di licenza (default: standard)")
    p_gen.add_argument("--seats",    type=int, default=1, metavar="N",
                       help="Numero massimo di istanze simultanee (default: 1)")
    p_gen.add_argument("--expiry",   default=None, metavar="YYYY-MM-DD",
                       help="Data di scadenza ISO (es. 2027-12-31). Omettere per licenza perpetua.")
    p_gen.add_argument("--hardware", default=None, metavar="ID",
                       help="Fingerprint hardware a cui vincolare la licenza (16 hex).")
    p_gen.add_argument("--bind-local", action="store_true",
                       help="Vincola automaticamente al computer corrente (ignora --hardware).")
    p_gen.add_argument("--out",      default="foliarium.license", metavar="FILE",
                       help="File di output (default: foliarium.license)")
    p_gen.set_defaults(func=cmd_generate)

    # --- inspect ---
    p_ins = sub.add_parser("inspect", help="Mostra informazioni di un file .license")
    p_ins.add_argument("file", help="Percorso del file .license da ispezionare")
    p_ins.set_defaults(func=cmd_inspect)

    # --- fingerprint ---
    p_fp = sub.add_parser("fingerprint", help="Mostra il fingerprint hardware del computer")
    p_fp.set_defaults(func=cmd_fingerprint)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
