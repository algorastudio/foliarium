# File: crea_hash.py
import bcrypt
import getpass

try:
    # Chiede la password in modo sicuro (non la mostra mentre digiti)
    password = getpass.getpass("Passo 1 -> Inserisci la password per il nuovo utente: ")
    password_confirm = getpass.getpass("Conferma la password: ")

    if not password or not password_confirm:
        print("\nERRORE: La password non può essere vuota.")
    elif password != password_confirm:
        print("\nERRORE: Le password non coincidono.")
    else:
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        
        print("\n" + "="*50)
        print(" HASH GENERATO CON SUCCESSO. COPIA LA SEGUENTE RIGA: ")
        print(hashed_password.decode('utf-8'))
        print("="*50 + "\n")

except KeyboardInterrupt:
    print("\nOperazione annullata.")