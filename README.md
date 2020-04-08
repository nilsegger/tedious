# Tedious
Tedious is a framework which provides simple and extendable classes for creating an API with SQL persistence.

Out of the box Tedious offers implementations for:
1. **[Starlette](https://www.starlette.io/)**
2. **[PostgreSQL](https://www.postgresql.org/)**
3. **File storage**, files are stored in the filesystem and referenced using a SQL Table.
4. **Token authentication** using JSON Web Tokens.
5. **Models**, easily create models which can receive input from SQL rows.

## Installing the tedious library
1. `python3 setup.py sdist && pip3 install dist/tedious-1.0.tar.gz`
2. Now you can simply `import tedious`
3. In your `__main__` initialize the configuration by adding `tedious.config.load_config('config.ini')`

## Running Tests
1. First run `python3 setup.py dbtest` for setting up the database.
Make sure the `tests/config.ini` file contains the right credentials for your PostgreSQL database.
2. `python3 -m pytest tests/ -s`

## Hello World example
In this hello world example we will set up an API which will listen to the `/login` route and sign in the user using the Auth module.
Furhtermore we are going to add our custom HelloWorld resource.

1. Initialize Starlette to listen to `/login`
    ```python
    import tedious.config
    from tedious.asgi.starlette import ResourceController, StarletteApp
    from tedious.res import AuthResource
    from tedious.sql.postgres import PostgreSQLDatabase
    from starlette.routing import Route
    
    tedious.config.load_config('config.ini')
    
    controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))
    
    
    async def login(request):
        return await controller.handle(request, AuthResource())
    
    
    app = StarletteApp(controller, [Route('/login', login, methods=["POST", "PUT", "DELETE"])]).app
    ```

2. Now using a **POST** request on `/login` with the following json body you should receive a uuid, token and refresh token.
    ```json
    {
       "username": "username",
       "password": "password"
    }
    ```
    If the user does not exist, create the account with the `Auth.register()` method.  
    With a **PUT** request containing the refresh token in the body as bytes, users are able to retrieve a fresh access token, and with **DELETE**, refresh tokens will be revoked.
    
3. Creating a custom Resource
    ```python
   class HelloWorldResource(ResourceInterface):

       async def on_get(self, request: RequestInterface, **kwargs) -> ResponseInterface:
    
            if request.requester is None:
                # User is not signed in
                return PlainTextResponse('Hello World!')
            else:
                # user is signed in
                return PlainTextResponse('Hello {}!'.format(request.requester.uuid))


    async def hello_world(request):
        return await controller.handle(request, HelloWorldResource())

   # Add the hello_world route
   app = StarletteApp(controller, [Route('/login', login, methods=["POST", "PUT", "DELETE"]), 
           Route('/helloworld', hello_world, methods=["GET"])]).app
    ```

