from dataclasses import dataclass
from typing import Any, Iterable

from neo4j import GraphDatabase, Driver, Record
from neo4j.exceptions import ServiceUnavailable


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str


class Neo4jClient:
    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver: Driver = self._connect()
        self._database = config.database

    def _connect(self) -> Driver:
        return GraphDatabase.driver(
            self._config.uri, auth=(self._config.user, self._config.password)
        )

    def _reconnect(self) -> None:
        try:
            self._driver.close()
        finally:
            self._driver = self._connect()

    def close(self) -> None:
        self._driver.close()

    def run(self, query: str, parameters: dict[str, Any] | None = None) -> list[Record]:
        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(query, parameters or {})
                return list(result)
        except ServiceUnavailable:
            self._reconnect()
            with self._driver.session(database=self._database) as session:
                result = session.run(query, parameters or {})
                return list(result)

    def run_write(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        try:
            with self._driver.session(database=self._database) as session:
                session.execute_write(lambda tx: tx.run(query, parameters or {}).consume())
        except ServiceUnavailable:
            self._reconnect()
            with self._driver.session(database=self._database) as session:
                session.execute_write(lambda tx: tx.run(query, parameters or {}).consume())

    def run_many(
        self, query: str, parameters_list: Iterable[dict[str, Any]]
    ) -> None:
        params_list = list(parameters_list)
        try:
            with self._driver.session(database=self._database) as session:
                def _run_many(tx) -> None:
                    for params in params_list:
                        tx.run(query, params)

                session.execute_write(_run_many)
        except ServiceUnavailable:
            self._reconnect()
            with self._driver.session(database=self._database) as session:
                def _run_many(tx) -> None:
                    for params in params_list:
                        tx.run(query, params)

                session.execute_write(_run_many)
