import pytest
from unittest.mock import Mock, patch, MagicMock
from neo4j import GraphDatabase, Driver, Session, ManagedTransaction, Result
from neo4j.exceptions import (
    AuthError,
    ClientError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

from graph.connection import Neo4jConnection, with_retry, _RETRYABLE_EXCEPTIONS
from graph.exceptions import GraphConnectionError, QueryError


class TestWithRetryDecorator:
    def test_with_retry_success(self):
        mock_func = Mock(return_value="success")
        decorated_func = with_retry(max_attempts=3)(mock_func)

        result = decorated_func()

        assert result == "success"
        mock_func.assert_called_once()

    def test_with_retry_success_after_retry(self):
        call_count = 0
        def mock_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ServiceUnavailable("fail")
            return "success"

        mock_func = Mock(side_effect=mock_side_effect)
        decorated_func = with_retry(max_attempts=3, base_delay=0.01)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_with_retry_max_attempts_exceeded(self):
        mock_func = Mock(side_effect=ServiceUnavailable("always fail"))
        decorated_func = with_retry(max_attempts=3, base_delay=0.01)(mock_func)

        with pytest.raises(GraphConnectionError) as exc_info:
            decorated_func()

        assert "All 3 attempts failed" in str(exc_info.value)
        assert mock_func.call_count == 3

    def test_with_retry_non_retryable_exception(self):
        mock_func = Mock(side_effect=ValueError("non-retryable"))
        decorated_func = with_retry(max_attempts=3, base_delay=0.01)(mock_func)

        with pytest.raises(ValueError) as exc_info:
            decorated_func()

        assert str(exc_info.value) == "non-retryable"
        mock_func.assert_called_once()


class TestNeo4jConnectionInit:
    def test_init_with_default_parameters(self):
        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        assert conn._uri == "bolt://localhost:7687"
        assert conn._user == "neo4j"
        assert conn._password == "password"
        assert conn._database == "neo4j"
        assert conn._driver is None
        assert conn._pool_size == 50
        assert conn._acquisition_timeout == 60.0
        assert conn._max_retry_time == 30.0
        assert conn._connection_timeout == 30.0

    def test_init_with_custom_parameters(self):
        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            database="mydb",
            max_connection_pool_size=100,
            connection_acquisition_timeout=120.0,
            max_transaction_retry_time=60.0,
            connection_timeout=60.0
        )

        assert conn._uri == "bolt://localhost:7687"
        assert conn._user == "neo4j"
        assert conn._password == "password"
        assert conn._database == "mydb"
        assert conn._driver is None
        assert conn._pool_size == 100
        assert conn._acquisition_timeout == 120.0
        assert conn._max_retry_time == 60.0
        assert conn._connection_timeout == 60.0


class TestNeo4jConnectionConnect:
    def test_connect_success(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db = mocker.patch('graph.connection.GraphDatabase.driver', return_value=mock_driver)

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        conn.connect()

        mock_driver.verify_connectivity.assert_called_once()

        assert conn._driver == mock_driver

    def test_connect_already_connected(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.verify_connectivity.return_value = None
        mocker.patch('graph.connection.GraphDatabase.driver', return_value=mock_driver)

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        conn.connect()
        first_driver = conn._driver

        conn.connect()

        assert conn._driver == first_driver

    def test_connect_auth_error(self, mocker):
        mock_graph_db = mocker.patch('graph.connection.GraphDatabase.driver', side_effect=AuthError("auth failed"))
        mock_close = mocker.patch('graph.connection.Neo4jConnection.close')

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="wrong_password"
        )

        with pytest.raises(GraphConnectionError) as exc_info:
            conn.connect()

        assert "Authentication failed" in str(exc_info.value)
        mock_graph_db.assert_called_once()
        mock_close.assert_called_once()

    def test_connect_generic_exception(self, mocker):
        mock_graph_db = mocker.patch('graph.connection.GraphDatabase.driver', side_effect=Exception("generic error"))
        mock_close = mocker.patch('graph.connection.Neo4jConnection.close')

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        with pytest.raises(Exception) as exc_info:
            conn.connect()

        assert str(exc_info.value) == "generic error"
        mock_graph_db.assert_called_once()
        mock_close.assert_called_once()


class TestNeo4jConnectionClose:
    def test_close_when_not_connected(self):
        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        conn.close()
        assert conn._driver is None

    def test_close_when_connected(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.close.return_value = None

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        conn.close()

        mock_driver.close.assert_called_once()
        assert conn._driver is None

    def test_close_when_driver_close_fails(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.close.side_effect = Exception("close failed")

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        conn.close()

        mock_driver.close.assert_called_once()
        assert conn._driver is None


class TestNeo4jConnectionContextManager:
    def test_context_manager_enter(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db = mocker.patch('graph.connection.GraphDatabase.driver', return_value=mock_driver)

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        with conn as returned_conn:
            assert returned_conn is conn
            mock_graph_db.assert_called_once()
            mock_driver.verify_connectivity.assert_called_once()

    def test_context_manager_exit(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db = mocker.patch('graph.connection.GraphDatabase.driver', return_value=mock_driver)
        mock_driver_close = mocker.patch.object(mock_driver, 'close')

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        with conn:
            pass

        mock_graph_db.assert_called_once()
        mock_driver.verify_connectivity.assert_called_once()
        mock_driver_close.assert_called_once()


class TestNeo4jConnectionDriverProperty:

    def test_driver_when_connected(self, mocker):
        mock_driver = Mock(spec=Driver)

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        assert conn.driver == mock_driver

    def test_driver_when_not_connected(self):
        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        with pytest.raises(GraphConnectionError) as exc_info:
            _ = conn.driver

        assert "Not connected. Call connect() first." in str(exc_info.value)


class TestNeo4jConnectionIsConnectedProperty:
    def test_is_connected_when_not_connected(self):
        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )

        assert conn.is_connected is False

    def test_is_connected_when_connected_and_healthy(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.verify_connectivity.return_value = None

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        assert conn.is_connected is True
        mock_driver.verify_connectivity.assert_called_once()

    def test_is_connected_when_connected_but_unhealthy(self, mocker):
        mock_driver = Mock(spec=Driver)
        mock_driver.verify_connectivity.side_effect = Exception("connection lost")

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        assert conn.is_connected is False
        mock_driver.verify_connectivity.assert_called_once()


class TestNeo4jConnectionSession:
    def test_session_success(self, mocker):
        mock_session = Mock(spec=Session)
        mock_driver = Mock(spec=Driver)
        mock_driver.session.return_value = mock_session

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        with conn.session() as session:
            assert session == mock_session
            mock_driver.session.assert_called_once_with(database="neo4j")

        mock_session.close.assert_called_once()

    def test_session_with_custom_database(self, mocker):
        mock_session = Mock(spec=Session)
        mock_driver = Mock(spec=Driver)
        mock_driver.session.return_value = mock_session

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            database="custom_db"
        )
        conn._driver = mock_driver

        with conn.session(database="other_db") as session:
            assert session == mock_session
            mock_driver.session.assert_called_once_with(database="other_db")

        mock_session.close.assert_called_once()


class TestNeo4jConnectionExecuteRead:
    def test_execute_read_success(self, mocker):
        mock_record = Mock()
        mock_record.data.return_value = {"name": "test"}

        mock_result = Mock(spec=Result)
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))

        mock_tx = Mock(spec=ManagedTransaction)
        mock_tx.run.return_value = mock_result

        mock_session = Mock(spec=Session)
        mock_session.execute_read.side_effect = lambda func: func(mock_tx)

        mock_driver = Mock(spec=Driver)
        mock_driver.session.return_value = mock_session

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        query = "MATCH (n) RETURN n.name"

        result = conn.execute_read(query)

        assert result == [{"name": "test"}]
        mock_session.execute_read.assert_called_once()


    def test_execute_read_client_error(self, mocker):
        mock_session = Mock(spec=Session)
        mock_session.execute_read.side_effect = ClientError("query failed")

        mock_driver = Mock(spec=Driver)
        mock_driver.session.return_value = mock_session

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        query = "MATCH (n) RETURN n.name"

        with pytest.raises(QueryError) as exc_info:
            conn.execute_read(query)

        assert "Read query failed" in str(exc_info.value)


class TestNeo4jConnectionExecuteWrite:
    def _setup_mock_connection(self):
        mock_record = Mock()
        mock_record.data.return_value = {"id": 123}

        mock_result = Mock(spec=Result)
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))

        mock_tx = Mock(spec=ManagedTransaction)
        mock_tx.run.return_value = mock_result

        mock_session = Mock(spec=Session)
        mock_session.execute_write.side_effect = lambda func: func(mock_tx)

        mock_driver = Mock(spec=Driver)
        mock_driver.session.return_value = mock_session

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        return conn, mock_session, mock_tx

    def test_execute_write_success(self, mocker):
        conn, mock_session, mock_tx = self._setup_mock_connection()

        query = "CREATE (n:Test {name: $name}) RETURN id(n)"
        parameters = {"name": "test"}

        result = conn.execute_write(query, parameters)

        assert result == [{"id": 123}]
        mock_session.execute_write.assert_called_once()
        mock_tx.run.assert_called_once_with(query, parameters)

    def test_execute_write_success_without_parameters(self, mocker):
        conn, mock_session, mock_tx = self._setup_mock_connection()

        query = "CREATE (n:Test) RETURN id(n)"

        result = conn.execute_write(query)

        assert result == [{"id": 123}]
        mock_session.execute_write.assert_called_once()
        mock_tx.run.assert_called_once_with(query, {})

    def test_execute_write_client_error(self, mocker):
        mock_session = Mock(spec=Session)
        mock_session.execute_write.side_effect = ClientError("query failed")

        mock_driver = Mock(spec=Driver)
        mock_driver.session.return_value = mock_session

        conn = Neo4jConnection(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        conn._driver = mock_driver

        query = "CREATE (n:Test {name: $name})"

        with pytest.raises(QueryError) as exc_info:
            conn.execute_write(query)

        assert "Write query failed" in str(exc_info.value)