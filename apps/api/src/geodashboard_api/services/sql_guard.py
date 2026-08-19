"""Validation structurelle des requêtes PostGIS en lecture seule."""

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


class SqlGuardError(ValueError):
    """Requête refusée par la politique de lecture seule."""


FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Copy,
)
ALLOWED_ANONYMOUS_FUNCTIONS = {"st_area", "st_geometrytype", "st_astext", "st_x", "st_y"}


def validate_read_only_sql(query: str, row_limit: int = 200) -> str:
    """Parse une unique requête SELECT et impose schéma et limite."""
    if ";" in query.rstrip().rstrip(";"):
        raise SqlGuardError("Une seule instruction SQL est autorisée.")
    try:
        tree = parse_one(query, read="postgres")
    except ParseError as exc:
        raise SqlGuardError("La syntaxe SQL est invalide.") from exc
    if not isinstance(tree, (exp.Select, exp.Union)) or any(tree.find_all(*FORBIDDEN_NODES)):
        raise SqlGuardError("Seules les requêtes SELECT en lecture seule sont autorisées.")
    tables = list(tree.find_all(exp.Table))
    if not tables:
        raise SqlGuardError("La requête doit lire une vue autorisée.")
    for table in tables:
        if table.db != "geodashboard" or not table.name.startswith("v_"):
            raise SqlGuardError("Seules les vues geodashboard.v_* sont accessibles.")
    for function in tree.find_all(exp.Anonymous):
        if function.name.casefold() not in ALLOWED_ANONYMOUS_FUNCTIONS:
            raise SqlGuardError(f"Fonction SQL non autorisée : {function.name}")
    tree.set("limit", exp.Limit(expression=exp.Literal.number(row_limit + 1)))
    return tree.sql(dialect="postgres")
