# python-sqlalchemy-cerbos

An example application of integrating [Cerbos](https://cerbos.dev) with a [FastAPI](https://fastapi.tiangolo.com/) server using [SQLAlchemy](https://www.sqlalchemy.org/) as the ORM. Cerbos helps you super-charge your authorization implementation by writing context-aware access control policies for your application resources. Author access rules using an intuitive YAML configuration language, use your Git-ops infrastructure to test and deploy them and, make simple API requests to the Cerbos PDP to evaluate the policies and make dynamic access decisions.

## Dependencies

- Python 3.10
- Docker for running the [Cerbos Policy Decision Point (PDP)](https://docs.cerbos.dev/cerbos/latest/installation/container.html)

## Getting Started

1. Start up the Cerbos PDP instance docker container. This will be called by the FastAPI app to check authorization.

```bash
cd cerbos
./start.sh
```

2. Install python dependencies

```bash
# from project root
pdm install
```

3. Start the FastAPI dev server

```bash
pdm run demo
```

## Sample data

On startup, the app will create an in-memory SQLite instance, and populate it with some sample data - see [here](https://github.com/cerbos/python-sqlalchemy-cerbos/blob/main/app/models.py).

The following users will be created. Authentication is done via Basic authentication using the provided Usernames (password is omitted). The Role and Department is loaded from the database after successful authentication.

| ID  | Username | Role  | Department |
| --- | -------- | ----- | ---------- |
| 1   | alice    | Admin | IT         |
| 2   | john     | User  | Sales      |
| 3   | sarah    | User  | Sales      |
| 4   | geri     | User  | Marketing  |

## Policies

This example has a simple CRUD policy in place for a resource kind of `contact` - like a CRM system would have. The policy files can be found in the `cerbos/policies` folder [here](https://github.com/cerbos/python-sqlalchemy-cerbos/blob/main/cerbos/policies).

Should you wish to experiment with this policy, you can <a href="https://play.cerbos.dev/p/c6321e740o6KrZa9ibQGUaQayBwDZML1" target="_blank">try it in the Cerbos Playground</a>.

<a href="https://play.cerbos.dev/p/c6321e740o6KrZa9ibQGUaQayBwDZML1" target="_blank"><img src="docs/launch.jpg" height="48" /></a>

The [policy](./cerbos/policies/contact.yaml) expects one of two roles to be set on the principal - `admin` and `user` and an attribute which defines their department as either `Sales` or `Marketing`.

These roles are authorized as follows:

| Action   | Role: Admin | Derived Role: Owner (User) | Role: User, department: `Sales` | Role: User, department: `Marketing`             |
| -------- | ----------- | -------------------------- | ------------------------------- | ----------------------------------------------- |
| `read`   | Y           | Y                          | if Contact is active            | if Contact is active and opted in to marketing  |
| `update` | Y           | Y                          |                                 |                                                 |
| `delete` | Y           | Y                          |                                 |                                                 |
| `create` | Y           |                            | Y                               |                                                 |

## Example Requests

### Get all contacts

```
curl -i http://john@localhost:8000/contacts
```

### Get a contact

As a Sales user => `200 OK`

```
curl -i http://john@localhost:8000/contacts/2
```

As a Marketing user => `403 Unauthorized`

```
curl -i http://geri@localhost:8000/contacts/2
```
