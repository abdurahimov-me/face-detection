import json

from django.core.management.base import BaseCommand
from django.db.models import Q, Exists, OuterRef

from ....orders.models import ProductOrder
from ....products.models import Product, ProductImage, ProductSimilarity, ProductEmbed, SecondaryTag

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
        with open("products.json", "r") as f:
            products_id = json.load(f)

        ProductImage.objects.filter(product_id__in=products_id).delete()
        ProductSimilarity.objects.filter(similar_id__in=products_id).delete()
        ProductEmbed.objects.filter(product_id__in=products_id).delete()
        SecondaryTag.objects.filter(product_id__in=products_id).delete()
        Product.objects.filter(id__in=products_id).delete()
