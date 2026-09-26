"""Tests del `BcryptPasswordHasher` con bcrypt real.

Usa un costo bajo (permitido solo en tests) para que el hashing real siga siendo rápido.
"""

from ocr_rag.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher

_COSTO_DE_TEST = 4


async def test_hashear_y_verificar_password_correcto_devuelve_true() -> None:
    hasher = BcryptPasswordHasher(costo=_COSTO_DE_TEST)

    password_hash = await hasher.hashear("una-contraseña-cualquiera")

    assert await hasher.verificar("una-contraseña-cualquiera", password_hash) is True


async def test_verificar_password_incorrecto_devuelve_false() -> None:
    hasher = BcryptPasswordHasher(costo=_COSTO_DE_TEST)

    password_hash = await hasher.hashear("la-correcta")

    assert await hasher.verificar("la-incorrecta", password_hash) is False


async def test_verificar_hash_con_formato_invalido_devuelve_false() -> None:
    hasher = BcryptPasswordHasher(costo=_COSTO_DE_TEST)

    assert await hasher.verificar("cualquier-cosa", "esto-no-es-un-hash-bcrypt") is False
