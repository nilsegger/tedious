from distutils.command.install import install
from setuptools import setup
import asyncio




class SetupDatabase(install):
    """Drops existing tables and creates new ones."""

    async def setup_database(self, db_credentials):

        from tedious.auth.auth import Auth
        from tedious.sql.postgres import PostgreSQLDatabase
        from tedious.stg.storage_upload import StorageUploadController
        from tedious.stg.storage import Storage

        async with PostgreSQLDatabase(**db_credentials) as db:
            async with await db.acquire() as connection:
                await connection.execute("DROP TABLE if exists file_chunks; DROP TABLE if exists file_reservations;")
                await connection.execute("DROP TABLE if exists files; DROP TYPE IF EXISTS Mime;")
                await connection.execute("DROP TABLE if exists logins;")
                await connection.execute(';'.join([Auth.CREATE_LOGINS_TABLE, Storage.CREATE_FILES_TABLE,
                                                   StorageUploadController.CREATE_FILE_CHUNKS_TABLE]))

    def run(self):

        try:
            import tedious.config
        except ImportError:
            raise ValueError("Please install tedious library before using this command.")

        tedious.config.load_config('tedious/tests/config.ini')
        asyncio.get_event_loop().run_until_complete(self.setup_database(tedious.config.CONFIG["DB_CREDENTIALS"]))


setup(
    name='tedious',
    version='1.0',
    description='Python Backend library which uses SQL database to store data and Starlette to route requests.',
    author='Nils Egger',
    url='#',
    author_email='nils.egger@eggersoftware.dev',
    packages=['tedious', 'tedious.asgi', 'tedious.sql', 'tedious.auth', 'tedious.mdl', 'tedious.res', 'tedious.stg', 'tedious.batch', 'tedious.tests'],
     =['asyncpg', 'starlette', 'uvicorn', 'pytest', 'pytest-asyncio', 'PyJWT', 'aiofiles', 'pycryptodome', 'cryptography', 'ujson'],
    cmdclass={
        'testdb': SetupDatabase
    }
)
