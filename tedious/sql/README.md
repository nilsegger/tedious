# Structured Query Language
This module contains the SQL database interface which is used in this library.  
There is one complete implementation for the PostgreSQL database built with asyncpg.  
If you want to use your own database simply inherit the SQLInterface and SQLConnectionInterface.
The SQLInterface should be a long lived connection to the database,
while the SQLConnectionInterface should be short lived connections which are acquired by calling the SQLInterface.acquire function.