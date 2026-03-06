from app.graph.neo4j import Neo4jClient


def seed_sample_data(client: Neo4jClient) -> None:
    query = """
    MERGE (p:Person {id: "person-1"})
    SET p.full_name = "John Doe", p.nationality = "Unknown"
    MERGE (c:Company {id: "company-1"})
    SET c.name = "Acme Holdings", c.jurisdiction = "Unknown"
    MERGE (p)-[:DIRECTOR_OF]->(c)
    """
    client.run_write(query)


def seed_demo_graph(client: Neo4jClient) -> None:
    query = """
    MERGE (p1:Person {id: "demo-person-1"})
    SET p1.full_name = "Alice Johnson",
        p1.nationality = "United Kingdom",
        p1.aliases = ["Alice J."]
    MERGE (p2:Person {id: "demo-person-2"})
    SET p2.full_name = "Michael Johnson",
        p2.nationality = "United Kingdom"
    MERGE (c1:Company {id: "demo-company-1"})
    SET c1.name = "Harbor Holdings Ltd",
        c1.jurisdiction = "United Kingdom",
        c1.industry = "Logistics"
    MERGE (l1:Location {id: "demo-location-1"})
    SET l1.name = "London",
        l1.type = "city"
    MERGE (s1:SanctionList {name: "demo-watchlist"})
    SET s1.authority = "Demo",
        s1.risk_level = "high"
    MERGE (p1)-[:SPOUSE_OF]->(p2)
    MERGE (p1)-[:DIRECTOR_OF]->(c1)
    MERGE (c1)-[:REGISTERED_IN]->(l1)
    MERGE (p2)-[:LISTED_IN]->(s1)
    """
    client.run_write(query)
