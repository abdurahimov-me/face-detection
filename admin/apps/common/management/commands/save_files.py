import json

from django.core.management.base import BaseCommand
from django.db.models import Q, Exists, OuterRef

from ....orders.models import ProductOrder
from ....products.models import Product, ProductImage

NOT_GENERATING = -1
GENERATING = 0
MODERATING = 1
APPROVED = 2
REJECTED = 3
ACADEMIC = 1
PERSONAL = 2


class Command(BaseCommand):
    help = 'Delete products'
    sub = Exists(ProductOrder.objects.filter(product=OuterRef('id')))

    def handle(self, *args, **options):
        products = (
            Product.objects
            .annotate(has_order=self.sub).filter(Q(Q(status=REJECTED) | Q(deleted=True)), has_order=False)
        )
        products_id = products.values_list('id', flat=True)

        with open("products.json", "w") as f:
            json.dump(list(products_id), f, indent=4)

        images = ProductImage.objects.filter(product_id__in=products_id).values_list('image', flat=True)

        with open("images.json", "w") as f:
            json.dump(list(images), f, indent=4)

        files = products.values_list('file', flat=True)

        with open("files.json", "w") as f:
            json.dump(list(files), f, indent=4)
