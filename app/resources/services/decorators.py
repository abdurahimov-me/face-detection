import functools
import inspect

from fastapi import HTTPException


def permission(permission_func):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not getattr(self, f'method_{func.__name__}', False):
                setattr(self, f'method_{func.__name__}', True)
                if inspect.iscoroutinefunction(permission_func):
                    checking = await permission_func(db=self.db, user=self.user, payload=self.payload)
                else:
                    checking = permission_func(db=self.db, user=self.user, payload=self.payload)

                if checking is False:
                    raise HTTPException(status_code=403, detail='You do not have permission to perform this action')

            if inspect.iscoroutinefunction(func):
                return await func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)

        return wrapper

    return decorator
