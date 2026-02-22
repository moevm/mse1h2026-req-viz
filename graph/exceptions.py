class GraphError(Exception):
    """Базовое исключение модуля для работы с Neo4j."""


class ConnectionError(GraphError):
    """Ошибка подключения к Neo4j."""


class QueryError(GraphError):
    """Ошибка выполнения запроса к Neo4j."""