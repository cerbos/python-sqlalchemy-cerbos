import json
from datetime import datetime

import uvicorn
from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Principal, ResourceDesc, ResourceList, Resource
from cerbos_sqlalchemy import get_query
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select

from db.models import Contact, Session, User

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
        # use sqla core, as returned `row` objects have row._mapping dict conversion
        res = s.execute(select(User.__table__).where(User.username == username))

        # retrieve `user` from the DB to access the attributes
        user = res.fetchone()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    return Principal(user.id, roles=[user.role], attr=dict(user._mapping))


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
    print(query.compile(compile_kwargs={"literal_binds": True}))

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


def convert_datetime_to_string(obj: any) -> any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


@app.get("/contacts/{contact_id}")
async def get_contact(contact_id: int, p: Principal = Depends(get_principal)):
    with Session() as s:
        contact = s.execute(select(Contact.__table__).where(Contact.id == contact_id)).fetchone()
        if contact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found",
            )

    r = Resource(
        id=contact.id,
        kind="contact",
        attr={k: convert_datetime_to_string(v) for k, v in contact._mapping.items()},
    )

    with CerbosClient(host="http://localhost:3592") as c:
        if not c.is_allowed("read", p, r):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return contact


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
