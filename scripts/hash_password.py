"""Gera o hash da senha do administrador para o .env."""
import getpass
import sys

from werkzeug.security import generate_password_hash

pw = getpass.getpass("Senha do administrador: ")
if len(pw) < 10:
    sys.exit("Use ao menos 10 caracteres.")
if pw != getpass.getpass("Repita a senha: "):
    sys.exit("As senhas não conferem.")
print("\nCopie esta linha para o seu .env:\n")
print(f"ADMIN_PASSWORD_HASH='{generate_password_hash(pw)}'")
