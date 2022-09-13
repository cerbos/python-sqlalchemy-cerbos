import json

import uvicorn
from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Principal, Resource, ResourceDesc
from cerbos_sqlalchemy import get_query
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import delete, select

from app.models import Contact, Session, User
from app.schemas import ContactSchema

app = FastAPI()
security = HTTPBasic()


# Stored users:
#   "alice": "admin",
#   "john": "user",
#   "sarah": "user",
#   "geri": "user",
def get_principal(credentials: HTTPBasicCredentials = Depends(security)) -> Principal:
    username = credentials.username

    with Session() as s:
        # retrieve `user` from the DB to access the attributes
        user = s.scalars(select(User).where(User.username == username)).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    return Principal(user.id, roles={user.role}, attr={"department": user.department})


def get_db_contact(contact_id: str) -> Contact:
    with Session() as s:
        contact = s.scalars(select(Contact).where(Contact.id == contact_id)).first()
        if contact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found",
            )
    return contact


def get_resource_from_contact(
    db_contact: Contact = Depends(get_db_contact),
) -> Resource:
    return Resource(
        id=db_contact.id,
        kind="contact",
        attr=jsonable_encoder(
            {n.name: getattr(db_contact, n.name) for n in Contact.__table__.c}
        ),
    )


@app.get("/contacts")
async def get_contacts(p: Principal = Depends(get_principal)):
    with CerbosClient(host="http://localhost:3592") as c:
        rd = ResourceDesc("contact")

        # Get the query plan for "read" action
        plan = c.plan_resources("read", p, rd)
        print(json.dumps(plan.to_dict(), sort_keys=False, indent=4))

    query = get_query(
        plan,
        Contact,
        {
            "request.resource.attr.owner_id": User.id,
            "request.resource.attr.department": User.department,
            "request.resource.attr.is_active": Contact.is_active,
            "request.resource.attr.marketing_opt_in": Contact.marketing_opt_in,
        },
        [(Contact.owner_id, User.id)],
    )
    # print(query.compile(compile_kwargs={"literal_binds": True}))

    # Optionally reduce the returned columns (`with_only_columns` returns a new `select`)
    query = query.with_only_columns(
        Contact.id,
        Contact.first_name,
        Contact.last_name,
        Contact.is_active,
        Contact.marketing_opt_in,
    )

    with Session() as s:
        rows = s.execute(query).fetchall()

    return rows


@app.get("/contacts/{contact_id}")
async def get_contact(
    db_contact: Contact = Depends(get_db_contact), p: Principal = Depends(get_principal)
):
    r = get_resource_from_contact(db_contact)

    with CerbosClient(host="http://localhost:3592") as c:
        if not c.is_allowed("read", p, r):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
            )

    return db_contact


@app.post("/contacts/new")
async def create_contact(
    contact_schema: ContactSchema, p: Principal = Depends(get_principal)
):
    with CerbosClient(host="http://localhost:3592") as c:
        if not c.is_allowed(
            "create",
            p,
            Resource(
                id="new",
                kind="contact",
            ),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
            )

    db_contact = Contact(**contact_schema.dict())
    with Session() as s:
        s.add(db_contact)
        s.commit()
        s.refresh(db_contact)

    return {"result": "Created contact", "contact": db_contact}


@app.put("/contacts/{contact_id}")
async def update_contact(
    contact_schema: ContactSchema,
    db_contact: Contact = Depends(get_db_contact),
    p: Principal = Depends(get_principal),
):
    r = get_resource_from_contact(db_contact)

    with CerbosClient(host="http://localhost:3592") as c:
        if not c.is_allowed("update", p, r):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
            )

    for field, value in contact_schema:
        setattr(db_contact, field, value)

    with Session() as s:
        s.add(db_contact)
        s.commit()
        s.refresh(db_contact)

    return {"result": "Updated contact", "contact": db_contact}


@app.delete("/contacts/{contact_id}")
async def delete_contact(
    r: Resource = Depends(get_resource_from_contact),
    p: Principal = Depends(get_principal),
):

    with CerbosClient(host="http://localhost:3592") as c:
        if not c.is_allowed("delete", p, r):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized"
            )

    with Session() as s:
        s.execute(delete(Contact).where(Contact.id == r.id))
        s.commit()

    return {"result": f"Contact {r.id} deleted"}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
