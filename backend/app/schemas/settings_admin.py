from pydantic import BaseModel


class AppSettingRead(BaseModel):
    key: str
    current_value: str
    default_value: str
    is_override: bool


class AppSettingUpdate(BaseModel):
    value: str
