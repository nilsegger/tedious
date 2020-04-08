===
SQL
===

.. contents:: :local:

Introduction
============

The SQL module consists of a SQL connection class interface and a complete implementation for PostgreSQL.
Because database connections in a backend are often short-lived. There is a main long-lived connection
which spawns child collections which are short-lived.

Examples
========

---------------------
Executing a statement
---------------------

::

    from tedious.sql.postgres import PostgreSQLDatabase

    database = PostgreSQLDatabase(database='test', user='postgres', password='postgres')
    await database.connect()

    # retrieves a short lived connection
    connection = await database.acquire()
    await connection.execute("INSERT INTO users(display_name) VALUES($1)", "Ted")

----------------
Fetching a model
----------------

If you want to fetch a model from the database, make sure the to name the columns properly.
Imagine a table of users, which has a column referencing their profile picture in another table.

The statement would look like the following

::

    # The user model would have following fields
    # .display_name
    # .profile_picture
    #   ..uuid
    #   ..path

    stmt = "SELECT display_name, files.uuid as "profile_picture.uuid", files.path as "profile_picture.path" FROM users JOIN files ON users.profile_picture=files.uuid"
    user = await connection.fetch_models(User, stmt)

Classes
=======

------------
SQLInterface
------------

.. autoclass:: tedious.sql.interface.SQLInterface
    :members:

----------------------
SQLConnectionInterface
----------------------

.. autoclass:: tedious.sql.interface.SQLConnectionInterface
    :members:

------------------
PostgreSQLDatabase
------------------

.. autoclass:: tedious.sql.postgres.PostgreSQLDatabase
    :members:

---------------------
PostgreSQL Connection
---------------------

.. autoclass:: tedious.sql.postgres.Connection
    :members:
