from tedious.asgi.response_interface import ResponseInterface


class ResourceControllerInterface:
    """The resource controller controls a request from start to finish.
        It converts requests into instances of :class:`~tedious.asgi.request_interface.RequestInterface`
        and returns instances of :class:`~tedious.asgi.resource_interface.ResourceInterface` back to the requester."""

    async def run_safe(self, func, *args, **kwargs) -> ResponseInterface:
        """This method encapsulates all methods so that exceptions can be easily caught and handled.

        Args:
            func: Coroutine to be awaited.
            *args: Positional arguments to be passed along to func.
            **kwargs: Named arguments to be passed along to func.

        Returns:
            :class:`~tedious.asgi.resource_interface.ResourceInterface` returned by func.
        """
        try:
            if args is None and kwargs is None:
                return await func()
            elif args is not None and kwargs is None:
                return await func(*args)
            elif kwargs is not None and args is None:
                return await func(**kwargs)
            else:
                return await func(*args, **kwargs)
        except Exception as e:
            return await self.handle_exceptions(e)

    async def handle_exceptions(self, exception) -> ResponseInterface:
        """Converts exception into :class:`~tedious.asgi.resource_interface.ResourceInterface`.

        Returns:
            :class:`~tedious.asgi.resource_interface.ResourceInterface`
        """
        raise NotImplementedError

    async def handle(self, **kwargs) -> ResponseInterface:
        """This method should receive requests, convert them to :class:`~tedious.asgi.request_interface.RequestInterface` and
         run route request to :class:`tedious.asgi.resource_interface.ResourceInterface.on_request` and return a :class:`~tedious.asgi.resource_interface.ResourceInterface`.

         Returns:
            :class:`~tedious.asgi.resource_interface.ResourceInterface`"""
        raise NotImplementedError
