__all__ = (
    'SqlAlchemyRepository',
)

from sqlalchemy import func, exists, update, Select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select
from sqlalchemy.sql.elements import and_

from utils.exceptions import BadRequest
from .engine import db_helper


class SqlAlchemyRepository:
    db_helper = db_helper
    model = None

    def __init_subclass__(cls, **kwargs):
        """
        Ensures that any subclass of this repository has a defined `model`.
        """
        super().__init_subclass__(**kwargs)
        if not cls.model:
            raise ValueError("'model' must be defined")

    def select(self) -> Select[model]:
        return select(self.model)

    async def _with_session(self, _func, *args, **kwargs):
        """
        Helper method to manage session creation and cleanup.
        Wraps any method that requires a database session.
        """
        async with self.db_helper.session() as session:
            return await _func(session, *args, **kwargs)

    # Public Methods
    async def create[T](self, data: dict, commit=True, refresh=True) -> T:
        """
        Creates a new record in the database.

        Args:
            data (dict): The data to create a new record.
            commit (bool, optional): Whether to commit changes to the database.
            refresh (bool, optional): Whether to refresh the database.

        Returns:
            The newly created instance.
        """
        return await self._with_session(self.db_create, data, commit, refresh)

    async def get[T](self, **kwargs) -> T:
        """
        Retrieves a single record by unique conditions.

        Args:
            kwargs: Conditions to filter the record.

        Returns:
            The retrieved instance.

        Raises:
            NoResultFound: If no record is found.
        """
        return await self._with_session(self.db_get, **kwargs)

    async def get_or_create(self, defaults: dict = None, commit=True, **kwargs):
        """
        Retrieves an existing record or creates a new one if it does not exist.

        Args:
            defaults (dict): Additional fields to use when creating a new record.
            commit (bool, optional): Whether to commit changes to the database.
            kwargs: Conditions to locate an existing record.

        Returns:
            Tuple containing the instance and a boolean indicating if it was created.
        """
        return await self._with_session(self.db_get_or_create, defaults, commit, **kwargs)

    async def filter(self, order_by=None, **filters):
        """
        Finds multiple records based on dynamic filters.

        Args:
            filters (dict): Conditions in the format "field__operation".
            order_by (str, optional): Order records by this field.

        Returns:
            List of model instances that match the filters.
        """
        return await self._with_session(self.db_filter, order_by, **filters)

    async def find(self, **kwargs):
        """
        Finds multiple records that match the given conditions.

        Args:
            kwargs: Conditions to filter the records.

        Returns:
            List of matching instances.
        """
        return await self._with_session(self.db_find, **kwargs)

    async def delete(self, commit=True, **kwargs):
        """
        Deletes a record that matches the specified conditions.

        Args:
            kwargs: Conditions to filter the record.
            commit (bool, optional): Whether to commit changes to the database.

        Returns:
            The deleted instance.

        Raises:
            NoResultFound: If no record is found.
        """
        return await self._with_session(self.db_delete, commit, **kwargs)

    async def update_instance[T](
            self,
            data: dict,
            commit=True,
            refresh=True,
            instance: T = None,
            **kwargs
    ):
        return await self._with_session(self.db_update_instance, data, commit, refresh, instance, **kwargs)

    async def update(self, data: dict, commit=True, **kwargs):
        """
        Updates a record based on the given conditions.

        Args:
            data (dict): The data to update.
            commit (bool, optional): Whether to commit changes to the database.
            kwargs: Conditions to locate the record.

        Returns:
            The updated instance.

        Raises:
            NoResultFound: If no record is found.
        """
        return await self._with_session(self.db_update, data, commit, **kwargs)

    async def count(self, **kwargs):
        """
        Counts the number of records that match the specified conditions.

        Args:
            kwargs: Conditions to filter the records.

        Returns:
            The count of matching records.
        """
        return await self._with_session(self.db_count, **kwargs)

    async def bulk_create[T](self, objects: list[T], commit=True, ):
        """
        Adds multiple records to the database.

        Args:
            objects (list[T]): List of data dictionaries to create records.
            commit (bool, optional): Whether to commit changes to the database.

        Returns:
            List of created instances.
        """
        return await self._with_session(self.db_bulk_create, objects, commit)

    async def update_or_create(self, data: dict, defaults: dict = None, commit=True, **kwargs):
        """
        Updates an existing record if it exists; otherwise, creates a new one.

        Args:
            data (dict): Data for the new record.
            defaults (dict): Fields to update if the record exists.
            commit (bool, optional): Whether to commit changes to the database.
            kwargs: Conditions to locate the record.

        Returns:
            Tuple containing the instance and a boolean indicating if it was created.
        """
        return await self._with_session(self.db_update_or_create, data, defaults, commit, **kwargs)

    async def get_all(self):
        """
        Retrieves all records without any filtering.

        Returns:
            List of all instances.
        """
        return await self._with_session(self.db_get_all)

    async def paginate(self, limit: int, offset: int = 0, **kwargs):
        """
        Retrieves records with pagination.

        Args:
            limit (int): Number of records to retrieve.
            offset (int): Number of records to skip.
            kwargs: Conditions to filter the records.

        Returns:
            List of instances for the current page.
        """
        return await self._with_session(self.db_paginate, limit, offset, **kwargs)

    async def get_ordered(self, order_field, descending=False, **kwargs):
        """
        Retrieves records ordered by a specified field.

        Args:
            order_field: The field to order by.
            descending (bool): Whether to sort in descending order.
            kwargs: Conditions to filter the records.

        Returns:
            List of ordered instances.
        """
        return await self._with_session(self.db_get_ordered, order_field, descending, **kwargs)

    async def first(self, **kwargs):
        """
        Retrieves the first record that matches the conditions.

        Args:
            kwargs: Conditions to filter the record.

        Returns:
            The first matching instance or None.
        """
        return await self._with_session(self.db_first, **kwargs)

    async def exists(self, **kwargs) -> bool:
        """
        Checks if a record exists in the database with the provided conditions.

        Args:
            kwargs: Conditions to filter the record.

        Returns:
            bool: True if the record exists, otherwise False.
        """
        return await self._with_session(self.db_exists, **kwargs)

    async def last(self, **kwargs):
        """
        Retrieves the last record that matches the conditions.

        Args:
            kwargs: Conditions to filter the record.

        Returns:
            The last matching instance or None.
        """
        return await self._with_session(self.db_last, **kwargs)

    async def collect_conditions(self, filters: dict):

        """
        filters: Dictionary of filters with keys in the format "field__operation".
                     Supported operations: eq, ne, lt, lte, gt, gte, in, like, ilike.
        :param filters:
        :return:
        """
        conditions = []
        for key, value in filters.items():
            # Split the field name and operation
            field_name, *operation = key.split("__")
            operation = operation[0] if operation else "eq"

            # Get the actual model field
            field = getattr(self.model, field_name, None)
            if field is None:
                raise ValueError(f"Invalid field: {field_name}")

            # Apply different filter operations
            if operation == "eq":  # Equals
                conditions.append(field == value)
            elif operation == "ne":  # Not equal
                conditions.append(field != value)
            elif operation == "lt":  # Less than
                conditions.append(field < value)
            elif operation == "lte":  # Less than or equal
                conditions.append(field <= value)
            elif operation == "gt":  # Greater than
                conditions.append(field > value)
            elif operation == "gte":  # Greater than or equal
                conditions.append(field >= value)
            elif operation == "in":  # In list
                conditions.append(field.in_(value))
            elif operation == "like":  # SQL LIKE
                conditions.append(field.like(value))
            elif operation == "ilike":  # Case-insensitive LIKE
                conditions.append(field.ilike(value))
            else:
                raise ValueError(f"Unsupported filter operation: {operation}")
        return conditions

    async def apply_filters(self, query, filters: dict):
        """
        Applies dynamic filters to a query.

        Args:
            query: SQLAlchemy query object.
            filters: Dictionary of filters with keys in the format "field__operation".
                     Supported operations: eq, ne, lt, lte, gt, gte, in, like, ilike.

        Returns:
            Updated query with applied filters.
        """
        conditions = await self.collect_conditions(filters)
        return query.filter(and_(*conditions))

    async def db_create(self, session, data: dict, commit=True, refresh=True):
        instance = self.model(**data)
        session.add(instance)
        if commit:
            await session.commit()
        if refresh:
            await session.refresh(instance)

        return instance

    async def db_get(self, session, **kwargs):
        conditions = await self.collect_conditions(kwargs)
        stmt = select(self.model).filter(*conditions)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            raise BadRequest(f"{self.model.__name__} object dose not exist with {kwargs}")
        return instance

    async def db_get_or_create(self, session, defaults: dict = None, commit=True, **kwargs):
        stmt = select(self.model).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            return instance, False

        combined_data = {**kwargs, **(defaults or {})}
        instance = self.model(**combined_data)
        session.add(instance)

        if commit:
            await session.commit()
        return instance, True

    async def db_filter(self, session, order_by=None, **filters):
        ordering = order_by or [self.model.id.desc()]
        query = select(self.model)
        query = await self.apply_filters(query, filters)
        query = query.order_by(*ordering)
        result = await session.execute(query)
        return result.scalars().all()

    async def db_find(self, session, **kwargs):
        stmt = select(self.model).filter_by(**kwargs)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def db_delete(self, session, commit=True, **kwargs):
        stmt = select(self.model).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            await session.delete(instance)
            if commit:
                await session.commit()
            return instance
        else:
            raise NoResultFound(f"{self.model.__name__} not found with {kwargs}")

    async def db_update(self, session, data: dict, commit=True, **kwargs):
        conditions = await self.collect_conditions(kwargs)

        stmt = (
            update(self.model)
            .where(*conditions)
            .values(**data)
            .execution_options(synchronize_session="fetch")
            .returning(self.model)
        )
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance:
            if commit:
                await session.commit()
            return instance
        else:
            raise BadRequest(f"{self.model.__name__} not found with {kwargs}")

    async def db_count(self, session, **kwargs):
        stmt = select(func.count()).select_from(self.model).filter_by(**kwargs)
        result = await session.execute(stmt)
        return result.scalar()

    async def db_bulk_create[T](self, session, objects: list[T], commit=True):
        session.add_all(objects)
        await session.commit()
        return objects

    async def db_update_instance[T](
            self,
            session,
            data: dict,
            commit=True,
            refresh=True,
            instance: T = None,
            **kwargs,
    ):
        if instance is None:
            instance = await self.db_get(session, **kwargs)
        else:
            await session.merge(instance)

        for key, value in data.items():
            setattr(instance, key, value)

        if commit:
            await session.commit()

        if refresh:
            await session.refresh(instance)
        return instance

    async def db_update_or_create(self, session, data: dict, defaults: dict = None, commit=True, **kwargs):
        stmt = select(self.model).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()

        if instance:
            for key, value in (defaults or {}).items():
                setattr(instance, key, value)
            created = False
        else:
            instance = self.model(**data)
            session.add(instance)
            created = True
        if commit:
            await session.commit()
        return instance, created

    async def db_get_all(self, session):
        stmt = select(self.model)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def db_last(self, session, **kwargs):
        stmt = select(self.model).filter_by(**kwargs).order_by(self.model.id.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def db_first(self, session, **kwargs):
        conditions = await self.collect_conditions(kwargs)
        stmt = select(self.model).filter(*conditions).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def db_exists(self, session, **kwargs):
        conditions = await self.collect_conditions(kwargs)
        stmt = select(exists().where(*conditions))
        return await session.scalar(stmt)

    async def db_paginate(self, session, limit: int, offset: int, **kwargs):
        stmt = select(self.model).filter_by(**kwargs).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def db_get_ordered(self, session, order_field, descending=False, **kwargs):
        stmt = select(self.model).filter_by(**kwargs)
        if descending:
            stmt = stmt.order_by(getattr(self.model, order_field).desc())
        else:
            stmt = stmt.order_by(getattr(self.model, order_field))
        result = await session.execute(stmt)
        return result.scalars().all()
