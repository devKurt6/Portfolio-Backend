import re
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator, model_validator

def clean(value):
    normalized = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value))
    return ''.join(c for c in normalized if not unicodedata.category(c).startswith('C')).strip()

class WallPost(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = ''
    text: str = ''
    emoji: str = '💬'
    website: str = Field(default='', max_length=1000)

    @field_validator('name', 'text', mode='before')
    @classmethod
    def normalize(cls, value):
        if not isinstance(value, str):
            raise ValueError('Use plain text.')
        return clean(value)

    @model_validator(mode='after')
    def validate_message(self):
        if self.website:
            return self
        if not 2 <= len(self.name) <= 24:
            raise ValueError('Name must be 2–24 characters.')
        if not 3 <= len(self.text) <= 300:
            raise ValueError('Message must be 3–300 characters.')
        if self.emoji not in ['', '💬', '👋', '✨', '❤️', '🔥', '🎉', '🚀', '😊', '👍', '💡', '🙏', '💪', '🌱', '⭐']:
            raise ValueError('Choose one of the provided emojis.')
        return self

class Report(BaseModel):
    reason: str | None = Field(default=None, max_length=300)

class Contact(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(min_length=10, max_length=5000)
    website: str = Field(default='', max_length=1000)
    @field_validator('name', 'message', mode='before')
    @classmethod
    def normalize(cls, value):
        if not isinstance(value, str):
            raise ValueError('Use plain text.')
        return clean(value)

class Chat(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(default='anonymous', max_length=100)
