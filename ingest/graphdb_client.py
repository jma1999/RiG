# ingest/graphdb_client.py
"""
GraphDB Client for RDF Graph Management.

This module provides a client interface for GraphDB (Ontotext GraphDB) to:
- Load Turtle files into repositories
- Execute SPARQL queries
- Export graphs as JSON-LD
- Manage repositories

For GraphDB Desktop, the default endpoint is typically:
- Repository REST API: http://localhost:7200/rest/repositories/{repo_name}
- SPARQL endpoint: http://localhost:7200/repositories/{repo_name}
"""
import os
import sys
import pathlib
import argparse
from typing import Optional, Dict, Any, List
import requests
from rdflib import Graph, URIRef
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE
import json


class GraphDBClient:
    """
    Client for interacting with GraphDB.
    
    Supports both GraphDB Desktop (local) and GraphDB Server deployments.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:7200",
        repository: str = "rig-ifcld",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize GraphDB client.
        
        Args:
            base_url: GraphDB base URL (default: http://localhost:7200 for Desktop)
            repository: Repository name
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.repository = repository
        self.username = username
        self.password = password
        
        # REST API endpoints
        self.repos_url = f"{self.base_url}/rest/repositories"
        self.repo_url = f"{self.repos_url}/{self.repository}"
        self.statements_url = f"{self.base_url}/repositories/{self.repository}/statements"
        self.transactions_url = f"{self.repo_url}/transactions"
        
        # SPARQL endpoints
        self.sparql_url = f"{self.base_url}/repositories/{self.repository}"
        self.sparql_query_url = f"{self.sparql_url}/statements"
        
        # Session for authenticated requests
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)
    
    def create_repository(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        ruleset: str = "empty"
    ) -> bool:
        """
        Create a new GraphDB repository.
        
        Args:
            title: Repository title
            description: Repository description
            ruleset: Inference ruleset (e.g., "empty", "rdfs", "owl-horst")
        
        Returns:
            True if repository was created successfully
        """
        if title is None:
            title = self.repository
        
        if description is None:
            description = f"Repository for {self.repository}"
        
        # Check if repository already exists
        if self.repository_exists():
            print(f"ℹ️  Repository '{self.repository}' already exists")
            return True
        
        # Create repository configuration
        config = {
            "id": self.repository,
            "title": title,
            "type": "graphdb:FreeSailRepository",
            "params": [
                {
                    "id": "ruleset",
                    "value": ruleset
                },
                {
                    "id": "query-timeout",
                    "value": "0"
                },
                {
                    "id": "throwQueryEvaluationExceptionOnTimeout",
                    "value": "false"
                }
            ]
        }
        
        try:
            response = self.session.post(
                self.repos_url,
                json=config,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code in [201, 200]:
                print(f"✅ Created repository '{self.repository}'")
                return True
            else:
                print(f"⚠️  Failed to create repository: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating repository: {e}")
            return False
    
    def repository_exists(self) -> bool:
        """Check if repository exists."""
        try:
            response = self.session.get(
                f"{self.repo_url}/size",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def load_turtle_file(
        self,
        turtle_path: str,
        context: Optional[str] = None,
        base_uri: Optional[str] = None
    ) -> bool:
        """
        Load a Turtle file into the GraphDB repository.
        
        Args:
            turtle_path: Path to Turtle (.ttl) file
            context: Optional context/graph URI
            base_uri: Optional base URI for resources
        
        Returns:
            True if loaded successfully
        """
        turtle_path = pathlib.Path(turtle_path)
        
        if not turtle_path.exists():
            raise FileNotFoundError(f"Turtle file not found: {turtle_path}")
        
        print(f"📤 Loading Turtle file into GraphDB: {turtle_path.name}")
        
        # Read Turtle file content
        with open(turtle_path, 'r', encoding='utf-8') as f:
            turtle_content = f.read()
        
        # Prepare headers
        headers = {
            "Content-Type": "application/x-turtle",
        }
        
        # Add context if provided
        if context:
            headers["X-GraphDB-Repository"] = context
        
        try:
            # Use SPARQL UPDATE INSERT DATA or REST API
            # For GraphDB, we'll use the REST API statements endpoint
            response = self.session.post(
                self.statements_url,
                data=turtle_content.encode('utf-8'),
                headers=headers,
                timeout=300  # 5 minutes for large files
            )
            
            if response.status_code in [204, 201, 200]:
                print(f"✅ Successfully loaded {turtle_path.name}")
                return True
            else:
                print(f"⚠️  Failed to load file: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error loading Turtle file: {e}")
            return False
    
    def execute_sparql_query(
        self,
        query: str,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Execute a SPARQL query against the repository.
        
        Args:
            query: SPARQL query string
            output_format: Output format ("json", "xml", "turtle")
        
        Returns:
            Query results as dictionary
        """
        sparql = SPARQLWrapper(self.sparql_url)
        
        if output_format == "json":
            sparql.setReturnFormat(JSON)
        elif output_format == "turtle":
            sparql.setReturnFormat(TURTLE)
        else:
            sparql.setReturnFormat(JSON)
        
        sparql.setQuery(query)
        
        if self.username and self.password:
            sparql.setCredentials(self.username, self.password)
        
        try:
            results = sparql.queryAndConvert()
            return results
        except Exception as e:
            print(f"❌ SPARQL query error: {e}")
            raise
    
    def export_as_jsonld(
        self,
        output_path: str,
        context: Optional[str] = None,
        base_uri: Optional[str] = None
    ) -> bool:
        """
        Export repository graph as JSON-LD.
        
        Args:
            output_path: Path to output JSON-LD file
            context: Optional context/graph URI
            base_uri: Optional base URI for resources
        
        Returns:
            True if export was successful
        """
        output_path = pathlib.Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Exporting GraphDB repository as JSON-LD: {output_path}")
        
        # Construct SPARQL query to get all triples
        query = """
        CONSTRUCT { ?s ?p ?o }
        WHERE { ?s ?p ?o }
        """
        
        if context:
            query = f"""
            CONSTRUCT {{ ?s ?p ?o }}
            WHERE {{ GRAPH <{context}> {{ ?s ?p ?o }} }}
            """
        
        try:
            # Execute CONSTRUCT query to get RDF graph
            results = self.execute_sparql_query(query, output_format="turtle")
            
            # Parse results as RDF graph
            graph = Graph()
            if isinstance(results, bytes):
                graph.parse(data=results.decode('utf-8'), format='turtle')
            else:
                graph.parse(data=str(results), format='turtle')
            
            # Convert to JSON-LD
            jsonld_data = graph.serialize(format='json-ld', indent=2)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(jsonld_data)
            
            print(f"✅ Exported JSON-LD to {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting JSON-LD: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        try:
            response = self.session.get(
                f"{self.repo_url}/size",
                timeout=10
            )
            
            if response.status_code == 200:
                size = response.json()
                return {
                    "repository": self.repository,
                    "statements": size.get("statements", 0),
                    "size": size
                }
            else:
                return {"error": f"Status {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="GraphDB client for RDF graph management"
    )
    parser.add_argument("--base-url", default="http://localhost:7200",
                       help="GraphDB base URL (default: http://localhost:7200)")
    parser.add_argument("--repository", default="rig-ifcld",
                       help="Repository name")
    parser.add_argument("--username", default=None, help="Username for authentication")
    parser.add_argument("--password", default=None, help="Password for authentication")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create repository
    create_parser = subparsers.add_parser("create", help="Create repository")
    
    # Load Turtle file
    load_parser = subparsers.add_parser("load", help="Load Turtle file")
    load_parser.add_argument("turtle_file", help="Path to Turtle file")
    load_parser.add_argument("--context", default=None, help="Context/graph URI")
    
    # Export JSON-LD
    export_parser = subparsers.add_parser("export", help="Export as JSON-LD")
    export_parser.add_argument("output", help="Output JSON-LD file path")
    export_parser.add_argument("--context", default=None, help="Context/graph URI")
    
    # Query
    query_parser = subparsers.add_parser("query", help="Execute SPARQL query")
    query_parser.add_argument("sparql", help="SPARQL query string")
    query_parser.add_argument("--format", default="json", choices=["json", "xml", "turtle"],
                             help="Output format")
    
    # Statistics
    stats_parser = subparsers.add_parser("stats", help="Get repository statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    client = GraphDBClient(
        base_url=args.base_url,
        repository=args.repository,
        username=args.username,
        password=args.password
    )
    
    try:
        if args.command == "create":
            success = client.create_repository()
            sys.exit(0 if success else 1)
            
        elif args.command == "load":
            success = client.load_turtle_file(args.turtle_file, context=args.context)
            sys.exit(0 if success else 1)
            
        elif args.command == "export":
            success = client.export_as_jsonld(args.output, context=args.context)
            sys.exit(0 if success else 1)
            
        elif args.command == "query":
            results = client.execute_sparql_query(args.sparql, output_format=args.format)
            print(json.dumps(results, indent=2))
            
        elif args.command == "stats":
            stats = client.get_statistics()
            print(json.dumps(stats, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

