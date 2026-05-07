import bcrypt

password = b"supervisor@sipra"

# Generar un 'salt' y luego el hash
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password, salt)

print(hashed)
