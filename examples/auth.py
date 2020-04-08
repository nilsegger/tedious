"""
    This example shows how to use the auth module.
"""

import tedious.config
from tedious.sql.postgres import PostgreSQLDatabase
from tedious.auth.auth import Auth

tedious.config.load_config('config.ini')

database = PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"])
await database.connect()
connection = await database.acquire()

# Registering a user
await Auth().register(connection, "username", "password", "role of user")
# Signing in
requester = await Auth().authenticate(connection, "username", "password")
# Deleting user
await Auth().delete(connection, requester)

# Creating an access token
token = await Auth().create_token(claims={'uid': requester.uuid,
                                          'name': requester.username})

# Validating a token
await Auth().validate_token(token)

# Creating a refresh token
refresh_token = await Auth().create_refresh_token(connection, requester)
# Validating a refresh token
requester = await Auth().validate_refresh_token(connection, refresh_token)
# Revoking a refresh token
await Auth().revoke_refresh_token(connection, requester)
