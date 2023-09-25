from pydantic import BaseModel


class ContactSchema(BaseModel):
    first_name: str
    last_name: str
    owner_id: str = ""
    company_id: str = ""
    is_active: bool = False
    marketing_opt_in: bool = False

    class Config:
        orm_mode = True


class UserSchema(BaseModel):
    username: str
    email: str
    name: str
    contacts: list[ContactSchema]
    role: str
    department: str

    class Config:
        orm_mode = True


class CompanySchema(BaseModel):
    name: str
    website: str
    contacts: list[ContactSchema]

    class Config:
        orm_mode = True
