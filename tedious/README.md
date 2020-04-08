# Tedious
tedious is a framework for backend API's.  

## asgi
This framework will run a server with the Asynchronous Server Gateway Interface (ASGI) protocol. 
Most implementations of ASGI, like Starlette, support the asyncio library.

## auth
API's work well with token based authentication. Tedious uses JWT implementations.

## mdl
A model consists of other models and fields. Only field contain values, models consist only of fields and other models. 
For model manipulation, extend the FormControllerInterface, which offers out of the box support for creating, updating and deleting models.
If you want to list your models, use the ListControllerInterface.

## sql
Basic SQL implementations, like PostgreSQL.

## stg  
Contains a storage interface class and a complete implementation using the filesystem and referencing the files using a SQL table.
Furthermore it contains a controller for uploading files as chunks.

## imps
The imps module contains complete implementations for authentication using JWT and SQL accompanied by its resource, which can be used by the ASGI module.
Furthermore it contains resources for model forms, model listing, image serving and image upload. Theses resources can all be used by the Starlette implementation.

## batch
A batch should increase performance or data usage by grouping together multiple identical commands.
Contains implementations for Auth, Storage and FormControllers.