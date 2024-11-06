# 🎩 Tirehtööri

Tirehtööri is a Django service that provides URL redirection functionality.

## 🚀 Features

- URL redirection with Django
- Customizable redirection rules
  - Support for 301/302 status codes
  - Simple wildcard matching
  - Append matched path and query parameters to the target URL
  - Support both case-insensitive and case-sensitive matching
- Support for multiple domains
- Import redirection rules from a JSON file

## 🛠️ Getting started


### 📋 Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)


### 🏗️ Setup

1. Make a copy of the example environment file:
    ```bash
    cp .env.example .env
    ```

2. Start the Docker containers:
    ```bash
    docker compose up
    ```

3. Access the application at `http://localhost:8000`.

## 📝 Usage

### Adding redirection rules

You can add redirection rules using the Django admin interface.

Each redirection rule belongs to a domain, so you need to create a domain first.
Note that when using localhost as a domain, you need to include the port number
in the domain name (e.g., `localhost:8000`).

The redirection rules do not support regular expressions.


### Wildcard matching in Tirehtööri

The `match_subpaths` option matches any path starting with the specified path, like
a wildcard. The `append_subpath` option appends the matched subpath to the target URL.

For example, with the path `/foo` and `match_subpaths` enabled, the rule matches
`/foo`, `/foo/bar`, `/foo/bar/baz`, etc. With the path `/foo`, destination
`acme.test`, and both options enabled, the rule matches `/foo/bar` and redirects
to `acme.test/bar`.

### Importing redirection rules

You can import redirection rules from a JSON file using the Django management command
`import_redirection_rules`.

```bash
docker compose exec django python manage.py import_redirection_rules path/to/rules.json
```

See `--help` for more information on the command:

```bash
docker compose exec django python manage.py import_redirection_rules --help
```

The JSON file should have the following structure:

```json5
[
  {
    "domain_names": ["acme.test", "www.acme.test"],
    "rules": [
      {
        // Required fields
        "path": "/foo",
        "destination": "https://foo.test/bar",
        // Optional fields
        "permanent": true,
        "case_sensitive": false,
        "match_subpaths": false,
        "append_subpath": false,
        "pass_query_string": false,
        "notes": "An optional note"
      },
      // ...more rules...
    ]
  }
]
```

## 🧪 Testing

Run the tests using pytest:
```bash
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
