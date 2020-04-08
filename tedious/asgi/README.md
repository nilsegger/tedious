# Asynchronous Server Gateway Interface
This module contains the following interfaces:
* Request interface  
This interface contains all important information about a request, like url, client ip, query parameters etc.
* Response interface  
The response interface stores all necessary information to respond to a request. (status code, response headers etc.)
* Resource interface  
The resource interface routes requests to functions. GET request will be executed by on_get
* Resource controller interface  
The resource controller interface simply handles requests and converts common responses into actual responses usable by the chosen ASGI framework.

## How these interfaces should be used
Upon a request, a chosen ResourceController shoud conver the request into an object which inherits the request interface,
after the conversion, the request is passed onto a resource, this resource routes the request onto the proper on_* function (on_get, on_post, on_put, on_delete), 
these functions should all return an object inheriting from the ResponseInterface which is then passed back to the resource controller,
the resource controller converts this response into an actual usable response by the ASGI framework.