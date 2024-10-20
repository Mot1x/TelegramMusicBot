from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    bot_token: str
    yandex_token: str
    storage_chat_id: int

    class Config:
        env_file = ('db.env', '.env')

    @property
    def database_url_asyncpg(self):
        return f'postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'


settings = Settings()
