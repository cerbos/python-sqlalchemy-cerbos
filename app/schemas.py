from typing import List

from pydantic import BaseModel


class ContactSchema(BaseModel):
    first_name: str
    last_name: str
    owner_id: str = ""
    company_id: str = ""
    is_active: bool = False
    marketing_opt_in: bool = False

    class Config:
        from_attributes = True


class UserSchema(BaseModel):
    username: str
    email: str
    name: str
    contacts: List[ContactSchema]
    role: str
    department: str

    class Config:
        from_attributes = True


class CompanySchema(BaseModel):
    name: str
    website: str
    contacts: List[ContactSchema]

    class Config:
        from_attributes = True
