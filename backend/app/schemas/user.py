from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    balance: float
    is_active: bool

    model_config = {"from_attributes": True}


class UserMeOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    balance: float
    is_active: bool

    model_config = {"from_attributes": True}
