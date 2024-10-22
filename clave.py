from cryptography.fernet import Fernet

# Generar una clave Fernet
fernet_key = Fernet.generate_key()
print(fernet_key.decode())  # Imprimir la clave en formato legible