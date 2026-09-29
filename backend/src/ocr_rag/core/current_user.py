"""Representación tipada del usuario autenticado."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Usuario autenticado, resuelto desde la base a partir del `sub` del JWT.

    `get_current_user` (en `api/security.py`) es el único lugar autorizado a construirlo.
    """

    id: int
    username: str
    nombre_completo: str
    roles: list[str] = field(default_factory=list)
    permisos: list[str] = field(default_factory=list)
