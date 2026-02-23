class GraphError(Exception):
    """Базовое исключение модуля для работы с Neo4j."""


class GraphConnectionError(GraphError):
    """Ошибка подключения к Neo4j."""


class QueryError(GraphError):
    """Ошибка выполнения запроса к Neo4j."""
