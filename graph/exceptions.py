class GraphError(Exception):
    """Базовое исключение модуля для работы с Neo4j."""


class GraphConnectionError(GraphError):
    """Ошибка подключения к Neo4j."""


class QueryError(GraphError):
    """Ошибка выполнения запроса к Neo4j."""


class NodeNotFoundError(GraphError):
    """Узел не найден в Neo4j."""


class RelationshipNotFoundError(GraphError):
    """Связь не найдена в Neo4j."""


class DuplicateNodeError(GraphError):
    """Узел уже существует в Neo4j."""


class InvalidFilterError(GraphError):
    """Неправильные параметры для фильтрации."""
